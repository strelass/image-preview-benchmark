import abc
import argparse
import enum
import os
import time
from pathlib import Path

import fitz
import pypdfium2 as pdfium
import pyvips
from pdf2image import convert_from_path
from wand.color import Color
from wand.image import Image

DEFAULT_DATA_PATH = Path(__file__).parent / "data"
DEFAULT_INPUT_PATH = DEFAULT_DATA_PATH / "input"
DEFAULT_OUTPUT_PATH = DEFAULT_DATA_PATH / "output"


@enum.unique
class GeneratorType(enum.StrEnum):
    WAND = "wand"
    PDF2IMAGE = "pdf2image"
    FITZ = "fitz"
    PYPDFIUM2 = "pypdfium2"
    PYVIPS = "pyvips"


class BasePreviewGenerator(abc.ABC):
    def create_preview(
        self,
        input_path: Path,
        output_path: Path,
        dpi: int,
        quality: int,
        image_type: str,
    ) -> None:
        start_time = time.perf_counter()
        try:
            self._create_preview(input_path, output_path, dpi, quality, image_type)
            end_time = time.perf_counter()
            duration = end_time - start_time
            print(
                f"{self.__class__.__name__} {input_path.name} {dpi=} {quality=} {image_type=}: {duration:.4f}",
            )
        except Exception as e:
            print(f"An error occurred with {self.__class__.__name__} preview generation: {e}")

    @abc.abstractmethod
    def _create_preview(
        self,
        input_path: Path,
        output_path: Path,
        dpi: int,
        quality: int,
        image_type: str,
    ) -> None: ...


class WandPreviewGenerator(BasePreviewGenerator):
    def _create_preview(
        self,
        input_path: Path,
        output_path: Path,
        dpi: int,
        quality: int,
        image_type: str,
    ) -> None:
        with Image(filename=f"{input_path}[0]", resolution=dpi) as img:
            img.background_color = Color("white")
            img.alpha_channel = "remove"
            img.transform_colorspace("srgb")
            img.format = image_type
            img.compression_quality = quality
            img.save(filename=str(output_path))


class Pdf2imagePreviewGenerator(BasePreviewGenerator):
    def _create_preview(
        self,
        input_path: Path,
        output_path: Path,
        dpi: int,
        quality: int,
        image_type: str,
    ) -> None:
        images = convert_from_path(
            input_path,
            dpi=dpi,
            first_page=1,
            last_page=1,
            fmt=image_type,
            thread_count=1,
        )
        if images:
            if image_type == "jpeg":
                images[0].save(str(output_path), "JPEG", quality=quality)
            else:
                compress_level = int(quality / 100 * 9)
                images[0].save(str(output_path), "PNG", compress_level=compress_level)


class FitzPreviewGenerator(BasePreviewGenerator):
    def _create_preview(
        self,
        input_path: Path,
        output_path: Path,
        dpi: int,
        quality: int,
        image_type: str,
    ) -> None:
        doc = fitz.open(input_path)
        try:
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=dpi)
            pix.save(output_path, image_type, jpg_quality=quality)
        finally:
            doc.close()


class Pypdfium2PreviewGenerator(BasePreviewGenerator):
    def _create_preview(
        self,
        input_path: Path,
        output_path: Path,
        dpi: int,
        quality: int,
        image_type: str,
    ) -> None:
        doc = pdfium.PdfDocument(input_path)
        page = doc[0]
        image = page.render(scale=dpi / 72).to_pil()
        if image_type == "jpeg":
            image.save(output_path, "JPEG", quality=quality)
        else:
            compress_level = int(quality / 100 * 9)
            image.save(output_path, "PNG", compress_level=compress_level)


class PyvipsPreviewGenerator(BasePreviewGenerator):
    def _create_preview(
        self,
        input_path: Path,
        output_path: Path,
        dpi: int,
        quality: int,
        image_type: str,
    ) -> None:
        image = pyvips.Image.new_from_file(str(input_path), dpi=dpi, page=0)
        if image_type == "jpeg":
            image.write_to_file(str(output_path), Q=quality)
        else:
            compression = int(quality / 100 * 9)
            image.write_to_file(str(output_path), compression=compression)


class PreviewGenerationEvaluator:
    __generators: dict[GeneratorType, BasePreviewGenerator] = {}

    def __init__(self, *, input_path: Path, output_path: Path) -> None:
        all_files = input_path.glob("*.pdf")
        self.input_files = [input_file for input_file in all_files if input_file.is_file()]
        self.input_files.sort(key=lambda input_file: input_file.name)
        self.output_path = output_path

        self.register_generator(GeneratorType.WAND, WandPreviewGenerator)
        self.register_generator(GeneratorType.PDF2IMAGE, Pdf2imagePreviewGenerator)
        self.register_generator(GeneratorType.FITZ, FitzPreviewGenerator)
        self.register_generator(GeneratorType.PYPDFIUM2, Pypdfium2PreviewGenerator)
        self.register_generator(GeneratorType.PYVIPS, PyvipsPreviewGenerator)

    def register_generator(
        self,
        generator_type: GeneratorType,
        generator: type[BasePreviewGenerator],
    ) -> None:
        self.__generators[generator_type] = generator()

    def run_preview_benchmark(
        self,
        *,
        generator_type: GeneratorType,
        dpi_set: list[int],
        quality_set: list[int],
        image_type: str,
    ) -> None:
        for dpi in dpi_set:
            for quality in quality_set:
                for input_file in self.input_files:
                    pure_name = os.path.splitext(input_file.name)[0]
                    output_dir = (
                        self.output_path / image_type / pure_name / str(dpi) / str(quality)
                    )
                    output_dir.mkdir(parents=True, exist_ok=True)
                    self.__generators[generator_type].create_preview(
                        input_path=input_file,
                        output_path=output_dir / f"{generator_type}.{image_type}",
                        dpi=dpi,
                        quality=quality,
                        image_type=image_type,
                    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--image-type",
        action="store",
        dest="image_type",
        choices=["jpeg", "png"],
        default="png",
    )
    parser.add_argument(
        "--generator-type",
        "-g",
        action="store",
        dest="generator_type",
        choices=[generator_type.value for generator_type in GeneratorType],
        required=True,
    )
    parser.add_argument(
        "--dpi-set",
        "-d",
        action="store",
        dest="dpi_set",
        type=int,
        nargs="+",
        default=[150, 200, 250],
    )
    parser.add_argument(
        "--quality-set",
        "-q",
        action="store",
        dest="quality_set",
        type=int,
        nargs="+",
        default=[75, 85, 95],
    )
    parser.add_argument(
        "--input-path",
        "-i",
        action="store",
        dest="input_path",
    )
    parser.add_argument(
        "--output-path",
        "-o",
        action="store",
        dest="output_path",
    )
    args = parser.parse_args()

    preview_generation_evaluator = PreviewGenerationEvaluator(
        input_path=Path(args.input_path) if args.input_path else DEFAULT_INPUT_PATH,
        output_path=Path(args.output_path) if args.output_path else DEFAULT_OUTPUT_PATH,
    )
    preview_generation_evaluator.run_preview_benchmark(
        generator_type=args.generator_type,
        dpi_set=args.dpi_set,
        quality_set=args.quality_set,
        image_type=args.image_type,
    )
