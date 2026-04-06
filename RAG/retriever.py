import os
import re
import sys
import importlib
from pathlib import Path

import chromadb
from dotenv import dotenv_values

try:
    from bytez import Bytez
except Exception:
    Bytez = None

sys.path.insert(0, str(Path(__file__).parent))
from embedder import get_embedder

RAG_DIR = Path(__file__).parent
ROOT_DIR = RAG_DIR.parent
STORE_PATH = RAG_DIR / "store"
ENV_PATH = ROOT_DIR / "env" / ".env"
COLLECTION_NAME = "jarvis_knowledge"
GITHUB_KNOWLEDGE_DIR = RAG_DIR / "knowledge" / "github"
LINKEDIN_KNOWLEDGE_DIR = RAG_DIR / "knowledge"
RESUME_KNOWLEDGE_FILES = [
    RAG_DIR / "knowledge" / "resume.md",
    RAG_DIR / "knowledge" / "abhi_resume.md",
]

_collection = None


def _read_key(name: str) -> str:
    val = os.getenv(name, "").strip()
    if val:
        return val
    if ENV_PATH.exists():
        return (dotenv_values(ENV_PATH).get(name) or "").strip()
    return ""


def _source_label(meta: dict | None) -> str:
    return Path((meta or {}).get("source", "unknown")).name


def _project_title(source: str) -> str:
    return source.replace("_profile.md", "").replace("_readmes.md", "")


def _extract_relevant_points(doc: str, limit: int = 4) -> list[str]:
    points = []
    for raw_line in doc.splitlines():
        line = raw_line.strip()
        if line.startswith("- "):
            text = re.sub(r"\s+", " ", line[2:]).strip()
            if text and "https://" in text:
                # Keep it readable by dropping trailing URL from long project lines.
                text = text.split("| https://")[0].strip()
            if text:
                points.append(text)
        if len(points) >= limit:
            break

    if points:
        return points

    plain = re.sub(r"<[^>]+>", " ", doc)
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", plain)
    return [s.strip() for s in sentences if s.strip()][:limit]


def _parse_project_line(line: str) -> dict | None:
    # Expected shape: ProjectName (Lang, *Stars): Description | topics: ...
    m = re.match(r"^\s*-\s*(?P<name>[^\(]+)\((?P<meta>[^\)]*)\):\s*(?P<desc>.+)$", line)
    if not m:
        return None

    name = m.group("name").strip()
    meta = m.group("meta").strip()
    desc = m.group("desc").strip()

    if "| topics:" in desc:
        desc = desc.split("| topics:", 1)[0].strip()
    if "| https://" in desc:
        desc = desc.split("| https://", 1)[0].strip()

    star_match = re.search(r"\*(\d+)", meta)
    stars = int(star_match.group(1)) if star_match else 0

    return {
        "name": name,
        "meta": meta,
        "desc": desc,
        "stars": stars,
    }


def _is_repo_query(query: str) -> bool:
    q = query.lower()
    repo_words = ["repo", "repos", "repository", "repositories", "github projects", "github repos"]
    return any(word in q for word in repo_words)


def _is_linkedin_query(query: str) -> bool:
    q = query.lower()
    return "linkedin" in q or "headline" in q or "experience" in q


def _select_profile_files_for_query(query: str) -> list[Path]:
    if not GITHUB_KNOWLEDGE_DIR.exists():
        return []

    profile_files = sorted(GITHUB_KNOWLEDGE_DIR.glob("*_profile.md"))
    if not profile_files:
        return []

    q = query.lower()
    selected = []
    for path in profile_files:
        stem = path.stem.lower()
        if "akshath" in q and "akshath" in stem:
            selected.append(path)
        elif "abhishek" in q and "abhishek" in stem:
            selected.append(path)

    return selected or profile_files


def _repos_from_profile(profile_path: Path) -> list[dict]:
    repos = []
    try:
        text = profile_path.read_text(encoding="utf-8")
    except Exception:
        return repos

    in_repo_section = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.strip().lower().startswith("## repositories"):
            in_repo_section = True
            continue
        if not in_repo_section:
            continue
        if line.strip().startswith("## "):
            break

        parsed = _parse_project_line(line)
        if parsed:
            repos.append(parsed)

    return repos


def _answer_repo_query(query: str) -> str:
    files = _select_profile_files_for_query(query)
    if not files:
        return "I could not find GitHub profile knowledge files yet."

    lines = []
    for profile_path in files:
        person = profile_path.stem.replace("_profile", "")
        repos = _repos_from_profile(profile_path)
        if not repos:
            continue

        repos.sort(key=lambda r: (-r["stars"], r["name"].lower()))
        lines.append(f"{person} has these notable GitHub repositories:")
        for i, repo in enumerate(repos[:10], start=1):
            desc = re.sub(r"\s+", " ", repo["desc"]).strip()
            if len(desc) > 95:
                desc = desc[:92].rstrip() + "..."
            lines.append(f"{i}. {repo['name']} - {desc}")
        lines.append("")

    if not lines:
        return "I found the profile files, but could not parse repository entries clearly."

    lines.append("This list is taken directly from your ingested GitHub profile repository sections.")
    return "\n".join(lines)


def _select_linkedin_files_for_query(query: str) -> list[Path]:
    files = sorted(LINKEDIN_KNOWLEDGE_DIR.glob("linkedin_*.md"))
    if not files:
        return []

    q = query.lower()
    selected = []
    for path in files:
        stem = path.stem.lower()
        if "akshath" in q and "akshatha" in stem:
            selected.append(path)
        elif "abhishek" in q and "abhishek" in stem:
            selected.append(path)
        elif "mystic" in q and "abhishek" in stem:
            selected.append(path)

    return selected or files


def _extract_section(text: str, heading: str) -> str:
    pattern = rf"##\s+[^\n]*{re.escape(heading)}[^\n]*\n(.*?)(?:\n---\n|\n##\s+|$)"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _extract_linkedin_summary(profile_path: Path) -> dict:
    text = profile_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("empty_linkedin_profile")

    title_match = re.search(r"^#\s+LinkedIn Profile\s+[—-]\s+(.+)$", text, flags=re.MULTILINE)
    name = title_match.group(1).strip() if title_match else profile_path.stem.replace("linkedin_", "").title()

    location_match = re.search(r"^(?:📍\s+|Location:\s+)(.+)$", text, flags=re.MULTILINE)
    location = location_match.group(1).strip() if location_match else "N/A"

    headline = _extract_section(text, "Headline").splitlines()[0].strip() if _extract_section(text, "Headline") else ""
    about = _extract_section(text, "About")
    about = re.sub(r"\s+", " ", about).strip()

    exp_block = _extract_section(text, "Experience")
    exp_titles = re.findall(r"###\s+(.+)$", exp_block, flags=re.MULTILINE)

    skills_block = _extract_section(text, "Skills")
    skills = []
    for line in skills_block.splitlines():
        s = line.strip()
        if s.startswith("* ") or s.startswith("- "):
            skills.append(s[2:].strip())

    return {
        "name": name,
        "location": location,
        "headline": headline,
        "about": about,
        "experience": exp_titles,
        "skills": skills,
    }


def _answer_linkedin_query(query: str) -> str:
    files = _select_linkedin_files_for_query(query)
    if not files:
        return "I could not find LinkedIn knowledge files yet."

    lines = []
    empty_files = []
    for path in files:
        try:
            info = _extract_linkedin_summary(path)
        except ValueError as exc:
            if str(exc) == "empty_linkedin_profile":
                empty_files.append(path.name)
            continue
        except Exception:
            continue

        lines.append(f"LinkedIn summary for {info['name']}:")
        lines.append(f"1. Location: {info['location']}")
        if info["headline"]:
            lines.append(f"2. Headline: {info['headline']}")
        if info["about"]:
            about = info["about"]
            if len(about) > 180:
                about = about[:177].rstrip() + "..."
            lines.append(f"3. About: {about}")
        if info["experience"]:
            top_roles = "; ".join(info["experience"][:2])
            lines.append(f"4. Experience: {top_roles}")
        if info["skills"]:
            top_skills = ", ".join(info["skills"][:6])
            lines.append(f"5. Key skills: {top_skills}")
        lines.append("")

    if not lines:
        if empty_files:
            file_list = ", ".join(empty_files)
            return (
                "I could not answer this LinkedIn query because these ingested files are empty: "
                f"{file_list}. Please re-create or re-ingest LinkedIn profile markdown content first."
            )
        return "I found LinkedIn files, but could not parse profile details clearly."

    lines.append("This summary is parsed directly from your ingested LinkedIn profile documents.")
    return "\n".join(lines)


def _is_resume_query(query: str) -> bool:
    q = query.lower()
    return any(
        word in q
        for word in [
            "resume",
            "cv",
            "internship",
            "intern",
            "education",
            "project",
            "experience",
            "skills",
            "cgpa",
            "gpa",
            "grade",
            "marks",
            "score",
        ]
    )


def _select_resume_files_for_query(query: str) -> list[Path]:
    q = query.lower()
    selected = []
    existing = [path for path in RESUME_KNOWLEDGE_FILES if path.exists()]
    for path in existing:
        stem = path.stem.lower()
        if "akshath" in q and "resume" in stem and "abhi" not in stem:
            selected.append(path)
        elif "abhishek" in q and "abhi" in stem:
            selected.append(path)

    return selected or existing


def _parse_resume_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_key = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line == "---":
            current_key = None
            continue

        if line.startswith("##"):
            heading = line.lstrip("# ").lower()
            if "summary" in heading:
                current_key = "summary"
            elif "intern" in heading or "experience" in heading:
                current_key = "experience"
            elif "project" in heading:
                current_key = "projects"
            elif "education" in heading:
                current_key = "education"
            elif "skill" in heading:
                current_key = "skills"
            else:
                current_key = None
            if current_key:
                sections.setdefault(current_key, [])
            continue

        if current_key:
            sections.setdefault(current_key, []).append(raw_line)

    return sections


def _extract_resume_section(text: str, section_name: str) -> str:
    sections = _parse_resume_sections(text)
    key = section_name.lower()
    if key == "internships":
        key = "experience"
    return "\n".join(sections.get(key, [])).strip()


def _collect_bullet_lines(block: str) -> list[str]:
    items = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if line.startswith("* ") or line.startswith("- "):
            item = re.sub(r"\s+", " ", line[2:]).strip()
            if item:
                items.append(item)
    return items


def _answer_resume_query(query: str) -> str:
    files = _select_resume_files_for_query(query)
    if not files:
        return "I could not find resume knowledge files yet."

    q = query.lower()
    want_internship = "intern" in q or "experience" in q
    want_project = "project" in q
    want_education = "education" in q or "study" in q or "cgpa" in q or "gpa" in q or "grade" in q or "marks" in q or "score" in q
    want_skills = "skill" in q

    lines = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            continue

        if path.stem.lower() == "resume":
            person = "Akshatha"
        elif path.stem.lower() == "abhi_resume":
            person = "Abhishek"
        elif "akshath" in query.lower():
            person = "Akshatha"
        elif "abhishek" in query.lower():
            person = "Abhishek"
        else:
            person = path.stem.replace("_resume", "").replace("resume", "").strip("_- ").title() or "Profile"

        sections = _parse_resume_sections(text)
        summary = "\n".join(sections.get("summary", [])).strip()
        internships = _collect_bullet_lines("\n".join(sections.get("experience", [])))
        experience = internships
        projects = _collect_bullet_lines("\n".join(sections.get("projects", [])))
        education = "\n".join(sections.get("education", [])).strip()
        education_bullets = _collect_bullet_lines(education)
        skills = _collect_bullet_lines("\n".join(sections.get("skills", [])))

        lines.append(f"Resume summary for {person}:")

        if summary:
            clean_summary = re.sub(r"\s+", " ", summary).strip()
            lines.append(f"1. Summary: {clean_summary}")

        section_index = 2
        if want_internship and internships:
            lines.append(f"{section_index}. Internship / experience:")
            for item in internships[:4]:
                lines.append(f"   - {item}")
            section_index += 1
        elif experience:
            lines.append(f"{section_index}. Experience:")
            for item in experience[:4]:
                lines.append(f"   - {item}")
            section_index += 1

        if want_project and projects:
            lines.append(f"{section_index}. Projects:")
            for item in projects[:4]:
                lines.append(f"   - {item}")
            section_index += 1

        if want_education and (education_bullets or education):
            lines.append(f"{section_index}. Education:")
            if education_bullets:
                for item in education_bullets[:3]:
                    lines.append(f"   - {item}")
            else:
                lines.append(f"   - {re.sub(r'\\s+', ' ', education).strip()}")
            section_index += 1

        if want_skills and skills:
            lines.append(f"{section_index}. Key skills:")
            for item in skills[:8]:
                lines.append(f"   - {item}")

        lines.append("")

    if not lines:
        return "I found resume files, but could not parse them clearly."

    lines.append("This answer is parsed directly from your resume documents.")
    return "\n".join(lines)


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(STORE_PATH))
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _search(query: str, k: int = 8, threshold: float = 0.75) -> list[dict]:
    collection = _get_collection()
    if collection.count() == 0:
        print("[search] knowledge store is empty. Run: python RAG/ingestor.py --reset")
        return []

    embedder = get_embedder()
    query_vec = embedder.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_vec],
        n_results=min(k, collection.count()),
        include=["documents", "distances", "metadatas"],
    )

    chunks = results["documents"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    matched = []
    for doc, dist, meta in zip(chunks, distances, metadatas):
        if dist <= threshold:
            matched.append({
                "doc": doc,
                "distance": dist,
                "meta": meta,
                "source": _source_label(meta),
            })

    if matched:
        print(f"[search] found {len(matched)} relevant chunks")
        return matched

    fallback = []
    for doc, dist, meta in zip(chunks[:3], distances[:3], metadatas[:3]):
        fallback.append({
            "doc": doc,
            "distance": dist,
            "meta": meta,
            "source": _source_label(meta),
        })
    print(f"[search] no strict matches, using top {len(fallback)} closest chunks")
    return fallback


def _build_context(items: list[dict]) -> str:
    blocks = []
    for item in items:
        blocks.append(f"Source: {item['source']}\n{item['doc']}")
    return "\n\n---\n\n".join(blocks)


def _extract_text_any(output) -> str:
    if isinstance(output, str):
        return output.strip()
    if isinstance(output, dict):
        for key in ("content", "text", "message", "output"):
            text = _extract_text_any(output.get(key))
            if text:
                return text
        return ""
    if isinstance(output, (list, tuple)):
        for item in output:
            text = _extract_text_any(item)
            if text:
                return text
        return ""
    if hasattr(output, "content"):
        return _extract_text_any(getattr(output, "content"))
    return ""


def _llm_explain(query: str, context: str) -> str:
    provider = os.getenv("RAG_LLM_PROVIDER", "bytez").strip().lower()

    if provider == "bytez":
        if Bytez is None:
            return ""
        api_key = _read_key("BYTEZ_API_KEY")
        if not api_key:
            return ""
        model_name = os.getenv("RAG_BYTEZ_MODEL", "openai/gpt-4o")
        model = Bytez(api_key).model(model_name)
        prompt = (
            "You are a helpful RAG answer generator.\n"
            "Use only the given context.\n"
            "Answer in simple language.\n"
            "Format:\n"
            "- 1 short summary line\n"
            "- Numbered points (3-6) if suitable\n"
            "- 1 short concluding insight\n"
            "Do not dump raw chunks.\n\n"
            f"Question: {query}\n\n"
            f"Context:\n{context}"
        )
        out = model.run([{"role": "user", "content": prompt}])
        return _extract_text_any(out)

    if provider == "groq":
        try:
            groq_module = importlib.import_module("groq")
            Groq = getattr(groq_module, "Groq")
        except Exception:
            return ""
        api_key = _read_key("GROQ_API_KEY")
        if not api_key:
            return ""
        model_name = os.getenv("RAG_GROQ_MODEL", "llama-3.1-8b-instant")
        client = Groq(api_key=api_key)
        out = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful RAG answer generator. "
                        "Use only the provided context and write concise, structured answers."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {query}\n\n"
                        f"Context:\n{context}\n\n"
                        "Respond with a short summary, numbered points when useful, and one-line conclusion."
                    ),
                },
            ],
            temperature=0.4,
            max_tokens=260,
        )
        return (out.choices[0].message.content or "").strip()

    return ""


def _fallback_explain(query: str, items: list[dict]) -> str:
    q = query.lower()

    if "project" in q or "built" in q:
        selected = items
        if "akshatha" in q:
            preferred = [it for it in items if "akshathaa" in it["source"].lower()]
            if preferred:
                selected = preferred
        elif "abhishek" in q:
            preferred = [it for it in items if "abhishek" in it["source"].lower()]
            if preferred:
                selected = preferred

        projects = []
        seen = set()
        for item in selected:
            for raw_line in item["doc"].splitlines():
                parsed = _parse_project_line(raw_line)
                if not parsed:
                    continue
                key = parsed["name"].lower()
                if key in seen:
                    continue
                seen.add(key)
                projects.append(parsed)

        if projects:
            projects.sort(key=lambda p: (-p["stars"], p["name"].lower()))
            person = "Akshatha" if "akshatha" in q else "Abhishek" if "abhishek" in q else "They"
            lines = [f"{person} has worked on several AI and software projects including:"]
            for i, p in enumerate(projects[:6], start=1):
                short_desc = re.sub(r"\s+", " ", p["desc"]).strip()
                if len(short_desc) > 120:
                    short_desc = short_desc[:117].rstrip() + "..."
                lines.append(f"{i}. {p['name']} - {short_desc}")
            lines.append("These projects show strong practical skills across AI, automation, and software systems.")
            return "\n".join(lines)

    by_source: dict[str, list[str]] = {}
    for item in items:
        source = item["source"]
        pts = _extract_relevant_points(item["doc"], limit=5)
        if pts:
            by_source.setdefault(source, []).extend(pts)

    if not by_source:
        return "I found related knowledge, but not enough clean details to explain this yet."

    lines = ["I found relevant info and here is a simple explanation:"]
    rank = 1
    for source, points in by_source.items():
        seen = set()
        unique_points = []
        for p in points:
            key = p.lower()
            if key not in seen:
                seen.add(key)
                unique_points.append(p)
        if not unique_points:
            continue

        title = _project_title(source)
        lines.append(f"{rank}. {title}:")
        lines.extend(f"   - {p}" for p in unique_points[:3])
        rank += 1

    if len(lines) == 1:
        return "I found matches, but could not format a clear summary."

    lines.append("These results show practical experience across AI and software systems.")
    return "\n".join(lines)


def answer_query(query: str, k: int = 8, threshold: float = 0.75) -> str:
    if _is_resume_query(query):
        print("[search] using direct resume parser...")
        return _answer_resume_query(query)

    if _is_linkedin_query(query):
        print("[search] using direct LinkedIn profile parser...")
        return _answer_linkedin_query(query)

    if _is_repo_query(query):
        print("[search] using direct GitHub repository parser...")
        return _answer_repo_query(query)

    print("[search] retrieving relevant chunks...")
    items = _search(query, k=k, threshold=threshold)
    if not items:
        return "I could not find relevant data in the knowledge base."

    print("[understand] building context and synthesizing answer...")
    context = _build_context(items)
    llm_answer = _llm_explain(query, context)
    if llm_answer:
        print("[explain] generated final answer")
        return llm_answer

    print("[explain] llm unavailable, using fallback explainer")
    return _fallback_explain(query, items)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else "what projects has Akshatha built"
    result = answer_query(query)
    print("\n=== ANSWER ===")
    print(result if result else "(nothing found)")