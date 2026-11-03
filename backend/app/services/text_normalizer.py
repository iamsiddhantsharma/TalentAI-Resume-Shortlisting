import re


class TextNormalizer:
    """
    Cleans extracted resume and Job Description text
    while preserving meaningful information and structure.

    Phase 4 responsibilities:
        - Normalize line endings
        - Normalize tabs
        - Normalize excessive spaces
        - Normalize blank lines
        - Remove invisible/control characters
        - Normalize common Unicode whitespace
        - Preserve meaningful line structure
        - Validate that usable text remains
    """

    def normalize(
        self,
        text: str,
    ) -> str:
        """
        Normalize extracted resume or Job Description text.

        Parameters
        ----------
        text:
            Raw text extracted from PDF, DOCX, TXT,
            or directly supplied by the user.

        Returns
        -------
        str
            Cleaned and normalized text.
        """

        # --------------------------------------------------
        # 1. Handle empty input
        # --------------------------------------------------

        if not text:
            return ""

        # --------------------------------------------------
        # 2. Normalize Unicode whitespace
        # --------------------------------------------------

        text = text.replace(
            "\u00a0",
            " ",
        )

        text = text.replace(
            "\u2007",
            " ",
        )

        text = text.replace(
            "\u202f",
            " ",
        )

        # --------------------------------------------------
        # 3. Normalize Windows / Mac line endings
        # --------------------------------------------------

        text = text.replace(
            "\r\n",
            "\n",
        )

        text = text.replace(
            "\r",
            "\n",
        )

        # --------------------------------------------------
        # 4. Remove invisible control characters
        #
        # Keep:
        #   \n  → meaningful line break
        #   \t  → handled below
        # --------------------------------------------------

        text = re.sub(
            r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]",
            "",
            text,
        )

        # --------------------------------------------------
        # 5. Replace tabs with spaces
        # --------------------------------------------------

        text = text.replace(
            "\t",
            " ",
        )

        # --------------------------------------------------
        # 6. Remove trailing spaces from every line
        # --------------------------------------------------

        lines = [
            line.rstrip()
            for line in text.split("\n")
        ]

        text = "\n".join(lines)

        # --------------------------------------------------
        # 7. Normalize excessive spaces
        #
        # Example:
        #
        # Python     Developer
        #
        # becomes:
        #
        # Python Developer
        # --------------------------------------------------

        text = re.sub(
            r"[ ]{2,}",
            " ",
            text,
        )

        # --------------------------------------------------
        # 8. Remove spaces immediately before/after
        # meaningful line boundaries
        # --------------------------------------------------

        lines = [
            line.strip()
            for line in text.split("\n")
        ]

        # --------------------------------------------------
        # 9. Remove excessive blank lines
        #
        # Maximum:
        #
        # one blank line between sections
        # --------------------------------------------------

        cleaned_lines: list[str] = []

        previous_blank = False

        for line in lines:

            if not line:

                if previous_blank:
                    continue

                cleaned_lines.append("")

                previous_blank = True

            else:

                cleaned_lines.append(line)

                previous_blank = False

        text = "\n".join(
            cleaned_lines
        )

        # --------------------------------------------------
        # 10. Remove leading/trailing blank lines
        # --------------------------------------------------

        text = text.strip()

        # --------------------------------------------------
        # 11. Final whitespace cleanup
        # --------------------------------------------------

        text = re.sub(
            r" +\n",
            "\n",
            text,
        )

        text = re.sub(
            r"\n +",
            "\n",
            text,
        )

        return text


text_normalizer = TextNormalizer()
