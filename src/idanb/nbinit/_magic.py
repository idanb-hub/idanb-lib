from __future__ import annotations

from IPython.core import magic

from idanb import meta


@magic.magics_class
class IdaNBMagics(magic.Magics):
    @magic.line_cell_magic
    def demo(self, line: str, cell: str | None = None) -> None:
        """Skip executing code in Voila."""
        if self.shell is None:
            return

        if meta.is_voila():
            return

        if cell is None:
            cell = line

        self.shell.run_cell(cell)
