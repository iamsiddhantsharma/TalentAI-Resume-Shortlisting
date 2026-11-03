import re


class TextNormalizer:
    """
    Normalizes extracted resume text before further processing.

    Responsibilities:
    - Normalize line endings
    - Remove null characters
    - Normalize whitespace
    - Remove excessive blank lines
    - Preserve meaningful resume structure
    """

    def normalize(self, text: str) -> str:
        """
        Normalize extracted resume text.

        Args:
            text: Raw text extracted from PDF, DOCX, or TXT.

        Returns:
            Cleaned and normalized text.
        """

        if not text:
            return ""

        # --------------------------------------------------
        # 1. Normalize line endings
        # --------------------------------------------------

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # --------------------------------------------------
        # 2. Remove null characters
        # --------------------------------------------------

        text = text.replace("\x00", "")

        # --------------------------------------------------
        # 3. Normalize tabs
        # --------------------------------------------------

        text = text.replace("\t", " ")

        # --------------------------------------------------
        # 4. Remove trailing spaces from every line
        # --------------------------------------------------

        lines = [
            line.strip()
            for line in text.split("\n")
        ]

        # --------------------------------------------------
        # 5. Remove excessive blank lines
        # --------------------------------------------------

        normalized_lines = []

        previous_blank = False

        for line in lines:

            if not line:
                if previous_blank:
                    continue

                normalized_lines.append("")
                previous_blank = True

            else:
                normalized_lines.append(line)
                previous_blank = False

        text = "\n".join(normalized_lines)

        # --------------------------------------------------
        # 6. Normalize excessive spaces
        # --------------------------------------------------

        text = re.sub(
            r"[ ]{2,}",
            " ",
            text,
        )

        # --------------------------------------------------
        # 7. Remove spaces around newlines
        # --------------------------------------------------

        text = re.sub(
            r" *\n *",
            "\n",
            text,
        )

        # --------------------------------------------------
        # 8. Limit excessive blank lines
        # --------------------------------------------------

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        # --------------------------------------------------
        # 9. Final cleanup
        # --------------------------------------------------

        return text.strip()


text_normalizer = TextNormalizer()
