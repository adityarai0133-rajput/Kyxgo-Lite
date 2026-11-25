import os
import re
import gc
import secrets
import sqlite3
import threading
from pathlib import Path
from datetime import datetime

try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PdfReader = None
    PDF_SUPPORT = False


class KyxgoCore:
    """
    Kyxgo Lite Offline Core Engine

    Features:
    - Offline SQLite FTS5 full-text search
    - TXT, MD, PY, and optional text-based PDF indexing
    - Saved and RAM-only temporary modes
    - Secure single-chat and full-history deletion
    - Hinglish & English follow-up context
    - Thread-safe database operations
    """

    SUPPORTED_EXTENSIONS = {
        ".txt",
        ".md",
        ".py",
        ".pdf"
    }

    def __init__(
        self,
        temp_mode=False,
        db_path="kyxgo_vault.db"
    ):
        self.temp_mode = bool(temp_mode)

        self.db_path = (
            ":memory:"
            if self.temp_mode
            else str(db_path)
        )

        self.last_context = ""
        self._lock = threading.RLock()
        self._closed = False

        if not self.temp_mode:
            Path(self.db_path).expanduser().parent.mkdir(
                parents=True,
                exist_ok=True
            )

        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30
        )

        self.conn.execute("PRAGMA busy_timeout = 30000")
        self.conn.execute("PRAGMA secure_delete = ON")

        if not self.temp_mode:
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.conn.execute("PRAGMA synchronous = NORMAL")

        self._setup_database()

    # --------------------------------------------------
    # DATABASE SETUP
    # --------------------------------------------------

    def _ensure_open(self):
        if self._closed:
            raise RuntimeError(
                "KyxgoCore database connection is closed."
            )

    def _setup_database(self):
        with self._lock:
            self._ensure_open()

            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
                USING fts5(
                    source_file,
                    content,
                    tokenize='porter unicode61'
                )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    source TEXT NOT NULL
                )
            """)

            self.conn.commit()

    # --------------------------------------------------
    # TEXT PROCESSING
    # --------------------------------------------------

    @staticmethod
    def _clean_text(text):
        if not text:
            return ""
        return text.replace("\x00", " ").strip()

    @staticmethod
    def _split_chunks(
        text,
        min_length=10,
        max_length=1800
    ):
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if len(paragraph) < min_length:
                continue

            if len(paragraph) <= max_length:
                chunks.append(paragraph)
                continue

            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            current = ""

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                if (
                    current
                    and len(current) + len(sentence) + 1 > max_length
                ):
                    if len(current) >= min_length:
                        chunks.append(current)
                    current = sentence
                else:
                    current = f"{current} {sentence}".strip()

            if len(current) >= min_length:
                chunks.append(current)

        return chunks

    # --------------------------------------------------
    # FILE EXTRACTION
    # --------------------------------------------------

    def _read_file(self, file_path):
        extension = file_path.suffix.lower()

        if extension in {".txt", ".md", ".py"}:
            try:
                return file_path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )
            except OSError:
                return ""

        if extension == ".pdf" and PDF_SUPPORT:
            try:
                reader = PdfReader(str(file_path))

                if reader.is_encrypted:
                    try:
                        if not reader.decrypt(""):
                            return ""
                    except Exception:
                        return ""

                pages = []
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        pages.append(page_text)

                return "\n\n".join(pages)
            except Exception:
                return ""

        return ""

    # --------------------------------------------------
    # KNOWLEDGE INDEXING
    # --------------------------------------------------

    def index_folder(self, folder_path="my_notes"):
        folder = Path(folder_path).expanduser()

        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
            welcome_file = folder / "welcome_guide.txt"

            if not welcome_file.exists():
                welcome_file.write_text(
                    "Kyxgo Lite Offline Engine: Ultra-fast offline study and code assistant.\n\n"
                    "Ohm's Law states that V = I * R at constant temperature.\n\n"
                    "Newton's Second Law states that Force equals mass multiplied by "
                    "acceleration (F = m * a).\n",
                    encoding="utf-8"
                )

        if not folder.is_dir():
            raise NotADirectoryError(f"Invalid notes folder: {folder}")

        records = []

        for file_path in folder.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            text_data = self._clean_text(self._read_file(file_path))
            if not text_data:
                continue

            try:
                source_name = str(file_path.relative_to(folder))
            except ValueError:
                source_name = file_path.name

            chunks = self._split_chunks(text_data)
            for chunk in chunks:
                records.append((source_name, chunk))

        with self._lock:
            self._ensure_open()

            with self.conn:
                self.conn.execute("DELETE FROM knowledge_fts")
                self.conn.executemany(
                    """
                    INSERT INTO knowledge_fts (source_file, content)
                    VALUES (?, ?)
                    """,
                    records
                )

        return len(records)

    # --------------------------------------------------
    # SEARCH QUERY BUILDER
    # --------------------------------------------------

    @staticmethod
    def _make_fts_query(text):
        tokens = re.findall(
            r"[^\W_]+",
            text,
            flags=re.UNICODE
        )

        unique_tokens = list(
            dict.fromkeys(
                token for token in tokens if len(token) > 1
            )
        )

        if not unique_tokens:
            return "", []

        query = " OR ".join(
            '"' + token.replace('"', '""') + '"'
            for token in unique_tokens
        )

        return query, unique_tokens

    # --------------------------------------------------
    # CRISP ANSWER EXTRACTION
    # --------------------------------------------------

    @staticmethod
    def _extract_crisp_answer(text, query_words):
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        if len(sentences) <= 2:
            return text.strip()

        query_words = {
            word.casefold()
            for word in query_words
            if len(word) > 1
        }

        scored = []

        for index, sentence in enumerate(sentences):
            sentence_words = {
                word.casefold()
                for word in re.findall(
                    r"[^\W_]+",
                    sentence,
                    flags=re.UNICODE
                )
            }

            score = len(query_words.intersection(sentence_words))

            if "=" in sentence or ":" in sentence:
                score += 1

            scored.append((score, index, sentence))

        scored.sort(key=lambda item: (-item[0], item[1]))
        selected = sorted(scored[:2], key=lambda item: item[1])

        return " ".join(item[2] for item in selected).strip()

    # --------------------------------------------------
    # ASK QUESTION
    # --------------------------------------------------

    def ask(self, question, save_chat=True):
        question = str(question or "").strip()

        if not question:
            return (
                "Kripya koi valid sawal likhein.",
                "System",
                None
            )

        clean_query = re.sub(r"[^\w\s]", " ", question).strip()
        _, words = self._make_fts_query(clean_query)

        if not words:
            return (
                "Kripya thoda detail mein sawal likhein.",
                "System",
                None
            )

        followup_markers = {
            "iska", "iski", "iske",
            "uska", "uski", "uske",
            "isme", "usme",
            "batao", "bata",
            "formula", "explain",
            "more", "this", "that",
            "it", "its", "them"
        }

        is_followup = (
            len(words) <= 2
            or any(word.casefold() in followup_markers for word in words)
        )

        with self._lock:
            self._ensure_open()

            if is_followup and self.last_context:
                search_terms = f"{self.last_context} {' '.join(words)}"
            else:
                search_terms = " ".join(words)
                self.last_context = " ".join(words[:4])

            fts_query, search_words = self._make_fts_query(search_terms)
            row = None

            if fts_query:
                try:
                    row = self.conn.execute(
                        """
                        SELECT source_file, content
                        FROM knowledge_fts
                        WHERE knowledge_fts MATCH ?
                        ORDER BY rank
                        LIMIT 1
                        """,
                        (fts_query,)
                    ).fetchone()
                except sqlite3.OperationalError:
                    row = None

            if row:
                source_file, raw_content = row
                answer_text = self._extract_crisp_answer(
                    raw_content,
                    search_words
                )
            else:
                source_file = "Offline Vault"
                answer_text = (
                    "Is topic par tumhare indexed notes ya "
                    "PDFs mein koi matching information nahi mili."
                )

            chat_id = None

            if save_chat and not self.temp_mode:
                timestamp = datetime.now().strftime("%d %b %Y, %I:%M %p")
                cursor = self.conn.execute(
                    """
                    INSERT INTO chat_history
                    (timestamp, question, answer, source)
                    VALUES (?, ?, ?, ?)
                    """,
                    (timestamp, question, answer_text, source_file)
                )
                self.conn.commit()
                chat_id = cursor.lastrowid

            return answer_text, source_file, chat_id

    # --------------------------------------------------
    # CHAT HISTORY
    # --------------------------------------------------

    def get_all_chats(self):
        with self._lock:
            self._ensure_open()

            if self.temp_mode:
                return []

            return self.conn.execute(
                """
                SELECT id, timestamp, question, answer, source
                FROM chat_history
                ORDER BY id ASC
                """
            ).fetchall()

    # --------------------------------------------------
    # DELETE SINGLE CHAT (SECURE OVERWRITE + DELETE)
    # --------------------------------------------------

    def delete_single_chat(self, chat_id):
        if self.temp_mode or chat_id is None:
            return False

        with self._lock:
            self._ensure_open()
            junk = secrets.token_hex(32)

            with self.conn:
                self.conn.execute(
                    """
                    UPDATE chat_history
                    SET question = ?, answer = ?, source = ?
                    WHERE id = ?
                    """,
                    (junk, junk, junk, int(chat_id))
                )
                cursor = self.conn.execute(
                    "DELETE FROM chat_history WHERE id = ?",
                    (int(chat_id),)
                )

            return cursor.rowcount > 0

    # --------------------------------------------------
    # WIPE ALL CHATS (SECURE OVERWRITE + DELETE)
    # --------------------------------------------------

    def wipe_all_chats(self):
        if self.temp_mode:
            return 0

        with self._lock:
            self._ensure_open()
            junk = secrets.token_hex(32)

            with self.conn:
                self.conn.execute(
                    """
                    UPDATE chat_history
                    SET question = ?, answer = ?, source = ?
                    """,
                    (junk, junk, junk)
                )
                cursor = self.conn.execute("DELETE FROM chat_history")

            return cursor.rowcount

    # --------------------------------------------------
    # RESET TOPIC CONTEXT
    # --------------------------------------------------

    def reset_context(self):
        with self._lock:
            self._ensure_open()
            self.last_context = ""

    # --------------------------------------------------
    # CLOSE AND CLEANUP
    # --------------------------------------------------

    def close_and_cleanup(self):
        with self._lock:
            if self._closed:
                return

            self.last_context = ""

            try:
                self.conn.close()
            finally:
                self._closed = True
                gc.collect()

    # --------------------------------------------------
    # CONTEXT MANAGER
    # --------------------------------------------------

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_and_cleanup()


# ------------------------------------------------------
# STANDALONE CORE TEST
# ------------------------------------------------------

if __name__ == "__main__":
    with KyxgoCore(temp_mode=False) as core:
        total = core.index_folder("my_notes")
        print(f"\n[Kyxgo Lite] Indexed Chunks: {total}")

        if not PDF_SUPPORT:
            print(
                "[Info] PDF support is unavailable. "
                "Install pypdf to enable PDF indexing."
            )

        while True:
            question = input("\nSawal pooch (ya 'exit' likh): ").strip()
            if question.casefold() == "exit":
                break

            answer, source, chat_id = core.ask(question)
            print(f"\nAnswer: {answer}")
            print(f"Source: {source} | Chat ID: {chat_id}")

    print("\n[Kyxgo Lite] Core closed.")
