import time
import os
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]

######## KILL SWITCH:   taskkill /IM llama-server.exe /F ####################

class PdfToMarkdownConverter:
    def __init__(self,
            input_dir: Path | str = repo_root / "papers",
            output_dir: Path | str = repo_root / "papers_md",
            mode: str = "balanced",
            disable_image_extraction: bool = True,
            page_range: list[int] | None = None,
            add_config: dict | None = None,
            # ustawienia plikow
            pattern: str = "*.pdf",
            search_subfolders: bool = False,
            overwrite_mds: bool = False,
            # ustawienia potrzebne do markera opisane w SETUP_MARKER.md
            backend: str = "llamacpp",
            llama_cpp_binary: str | None = None,
            parallel: int | None = 4,
            keep_alive: bool = False,
            hf_home: str | None = None
        ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.pattern = pattern
        self.search_subfolders = search_subfolders
        self.overwrite_mds = overwrite_mds
        self.save_images = not disable_image_extraction
        self._set_env(backend, llama_cpp_binary, parallel, keep_alive, hf_home)

        #jak zastanawiasz sie czemu wolno sie odpala to przez to: (laduje sie modele markera)
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.output import text_from_rendered

        self._text_from_rendered = text_from_rendered

        self.config = {
            "mode": mode,
            "disable_image_extraction": disable_image_extraction,
        }

        if page_range is not None:
            self.config["page_range"] = page_range
        if add_config:
            self.config.update(add_config)

        self.converter = PdfConverter(
            artifact_dict = create_model_dict(),
            config = self.config
        )

    @staticmethod
    def _set_env(backend, llama_cpp_binary, parallel, keep_alive, hf_home):
        os.environ["SURYA_INFERENCE_BACKEND"] = backend
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        if keep_alive:
            os.environ["SURYA_INFERENCE_KEEP_ALIVE"] = "1"
        if parallel is not None:
            os.environ["SURYA_INFERENCE_PARALLEL"] = str(parallel)
        if llama_cpp_binary:
            os.environ["LLAMA_CPP_BINARY"] = str(llama_cpp_binary)
        if hf_home:
            os.environ["HF_HOME"] = hf_home

    def find_pdfs(self) -> list[Path]:
        input_dir = self.input_dir.rglob if self.search_subfolders else self.input_dir.glob
        return sorted(input_dir(self.pattern))

    def output_path(self, pdf: Path | str) -> Path:
        relative = Path(pdf).relative_to(self.input_dir)
        return self.output_dir / relative.with_suffix(".md")

    def convert_file(self, pdf: Path | str) -> dict:
        pdf = Path(pdf)
        out = self.output_path(pdf)
        out.parent.mkdir(parents=True, exist_ok=True)

        t0 = time.perf_counter()
        rendered = self.converter(str(pdf))
        markdown, _, images = self._text_from_rendered(rendered)

        tmp = out.with_suffix(".md.tmp")
        tmp.write_text(markdown, encoding="utf-8")
        tmp.replace(out)

        if self.save_images and images:
            img_dir = out.parent
            for name, img in images.items():
                img.save(img_dir / name)

        seconds = time.perf_counter() - t0
        pages = len(rendered.metadata.get("page_stats", []))

        return {
            "file": pdf.name,
            "pages": pages,
            "seconds": seconds,
            "sec_per_page": seconds / max(pages, 1)
        }

    def convert_all(self) -> list[dict]:
        pdfs = self.find_pdfs()
        if not pdfs:
            print(f"Couldnt find any films in {self.pattern} format in {self.input_dir}")
            return []
        
        results = []

        for i, pdf in enumerate(pdfs, 1):
            info = f"[{i}/{len(pdfs)} {pdf.name}]"
            if self.output_path(pdf).exists() and not self.overwrite_mds:
                print(f"{info} skipping (already exists)")
                continue
            try:
                stats = self.convert_file(pdf)
                results.append(stats)
                print(f"{info}: {stats['pages']} pages, {stats['seconds']} seconds, {stats['sec_per_page']} seconds/pages")
            except Exception as e:
                print(f"{info}: error -> {type(e).__name__}: {e}")

        if results:
            total_pages = sum(r["pages"] for r in results)
            total_sec = sum(r["seconds"] for r in results)
            print(f"Summary: {len(results)} files, {total_pages} pages, {total_sec / 60:.1f} minutes")

        return results
        
if __name__ == "__main__":
    converter = PdfToMarkdownConverter(
        parallel=4,
        page_range=list(range(100,110))
    )
    converter.convert_all()


        
    
