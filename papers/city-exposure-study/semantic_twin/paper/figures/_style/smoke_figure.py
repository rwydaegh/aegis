"""Generate a small figure that exercises the shared paper style."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from paper_style import paper_style, save_figure, series_style

HERE = Path(__file__).resolve().parent


def main() -> None:
    x = np.linspace(0.0, 1.0, 13)
    with paper_style("single", height_ratio=0.68):
        figure, axis = plt.subplots()
        for index, scale in enumerate((0.45, 0.70, 0.95)):
            axis.plot(
                x,
                1.0 - np.exp(-x / scale),
                label=rf"$s={scale:.2f}$",
                **series_style(index, markevery=2),
            )
        axis.set(xlabel=r"Normalized distance $x$", ylabel=r"Cumulative fraction $F(x)$")
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.legend(loc="lower right", ncols=1)
        save_figure(figure, HERE / "smoke_figure.pdf")
        save_figure(figure, HERE / "smoke_figure.png", dpi=300)
        plt.close(figure)


if __name__ == "__main__":
    main()
