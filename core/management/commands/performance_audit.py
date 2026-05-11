import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run a lightweight performance audit across templates and static assets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            dest="as_json",
            action="store_true",
            help="Output the full audit as JSON.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Optional file path to store JSON report.",
        )

    def handle(self, *args, **options):
        report = {
            "templates": self.audit_templates(),
            "static": self.audit_static_assets(),
        }

        if options["output"]:
            output_path = Path(options["output"]).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Report written to {output_path}"))

        if options["as_json"]:
            self.stdout.write(json.dumps(report, indent=2))
            return

        self.print_human_report(report)

    def audit_templates(self):
        template_root = Path(settings.BASE_DIR) / "templates"
        if not template_root.exists():
            return {
                "count": 0,
                "total_size_kb": 0,
                "avg_size_kb": 0,
                "largest_templates": [],
                "images_missing_lazy": [],
            }

        template_files = sorted(template_root.rglob("*.html"))
        sizes = [(str(path.relative_to(settings.BASE_DIR)), path.stat().st_size) for path in template_files]

        missing_lazy = []
        image_pattern = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
        lazy_pattern = re.compile(r"\bloading\s*=\s*['\"]lazy['\"]", re.IGNORECASE)

        for path in template_files:
            text = path.read_text(encoding="utf-8", errors="ignore")
            image_tags = image_pattern.findall(text)
            missing = [tag for tag in image_tags if not lazy_pattern.search(tag)]
            if missing:
                missing_lazy.append(
                    {
                        "template": str(path.relative_to(settings.BASE_DIR)).replace("\\", "/"),
                        "missing_count": len(missing),
                    }
                )

        total_size = sum(size for _, size in sizes)
        count = len(sizes)
        largest = sorted(sizes, key=lambda item: item[1], reverse=True)[:10]

        return {
            "count": count,
            "total_size_kb": round(total_size / 1024, 2),
            "avg_size_kb": round((total_size / count) / 1024, 2) if count else 0,
            "largest_templates": [{"path": path.replace("\\", "/"), "size_kb": round(size / 1024, 2)} for path, size in largest],
            "images_missing_lazy": missing_lazy,
        }

    def audit_static_assets(self):
        project_root = Path(settings.BASE_DIR)
        static_roots = []

        root_static = project_root / "static"
        if root_static.exists():
            static_roots.append(root_static)

        for child in project_root.iterdir():
            app_static = child / "static"
            if child.is_dir() and app_static.exists():
                static_roots.append(app_static)

        static_roots = list(dict.fromkeys(static_roots))

        files = []
        for root in static_roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file():
                    rel = str(path.relative_to(settings.BASE_DIR)).replace("\\", "/")
                    files.append((rel, path.stat().st_size))

        total = sum(size for _, size in files)
        largest = sorted(files, key=lambda item: item[1], reverse=True)[:15]

        by_type = {"css": 0, "js": 0, "images": 0, "other": 0}
        for path, size in files:
            suffix = Path(path).suffix.lower()
            if suffix == ".css":
                by_type["css"] += size
            elif suffix == ".js":
                by_type["js"] += size
            elif suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif"}:
                by_type["images"] += size
            else:
                by_type["other"] += size

        return {
            "count": len(files),
            "total_size_mb": round(total / (1024 * 1024), 2),
            "largest_assets": [{"path": path, "size_kb": round(size / 1024, 2)} for path, size in largest],
            "size_by_type_mb": {k: round(v / (1024 * 1024), 2) for k, v in by_type.items()},
        }

    def print_human_report(self, report):
        templates = report["templates"]
        static = report["static"]

        self.stdout.write(self.style.MIGRATE_HEADING("\nPerformance Audit Summary"))
        self.stdout.write(f"Templates: {templates['count']} files, {templates['total_size_kb']} KB total")
        self.stdout.write(f"Static assets: {static['count']} files, {static['total_size_mb']} MB total")

        self.stdout.write(self.style.SUCCESS("\nTop Template Files"))
        for item in templates["largest_templates"][:5]:
            self.stdout.write(f"- {item['path']} ({item['size_kb']} KB)")

        self.stdout.write(self.style.SUCCESS("\nTop Static Assets"))
        for item in static["largest_assets"][:5]:
            self.stdout.write(f"- {item['path']} ({item['size_kb']} KB)")

        self.stdout.write(self.style.WARNING("\nTemplates missing lazy-loading on <img>"))
        if templates["images_missing_lazy"]:
            for item in templates["images_missing_lazy"][:10]:
                self.stdout.write(f"- {item['template']} ({item['missing_count']} tags)")
        else:
            self.stdout.write("- None detected")