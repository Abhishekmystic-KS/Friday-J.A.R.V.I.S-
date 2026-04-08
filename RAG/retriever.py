import json
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
_corpus_cache = None

QUERY_MEMORY_PATH = STORE_PATH / "query_memory.json"
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "did", "do", "does",
    "for", "from", "give", "has", "have", "he", "her", "his", "how", "i", "in",
    "is", "it", "me", "my", "of", "on", "or", "our", "she", "show", "tell",
    "that", "the", "their", "them", "they", "this", "to", "was", "we", "what",
    "when", "where", "which", "who", "why", "with", "you", "your",
}

TYPO_REPLACEMENTS = {
    "intership": "internship",
    "internnship": "internship",
    "internhsip": "internship",
    "eduction": "education",
    "educaton": "education",
    "collage": "college",
    "universitty": "university",
}


def _read_key(name: str) -> str:
    val = os.getenv(name, "").strip()
    if val:
        return val
    if ENV_PATH.exists():
        return (dotenv_values(ENV_PATH).get(name) or "").strip()
    return ""


def _source_label(meta: dict | None) -> str:
    return Path((meta or {}).get("source", "unknown")).name


def _normalize_company_name(raw: str) -> str:
    text = re.sub(r"\s+", " ", (raw or "")).strip().strip(".,;:")
    lower = text.lower()
    if "ai4sees" in lower or "ai4see" in lower:
        return "AI4SEES Pvt. Ltd."
    return text


def _normalize_person_name(raw: str) -> str:
    text = re.sub(r"\s+", " ", (raw or "")).strip().lower()
    if not text:
        return ""
    if "abhishek" in text:
        return "Abhishek"
    if "akshatha" in text:
        return "Akshatha"
    return ""


def _load_query_memory() -> dict:
    if not QUERY_MEMORY_PATH.exists():
        return {"history": []}
    try:
        data = json.loads(QUERY_MEMORY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("history", [])
            return data
    except Exception:
        pass
    return {"history": []}


def _save_query_memory(memory: dict) -> None:
    QUERY_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUERY_MEMORY_PATH.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")


def _remember_query(query: str, rewritten: str, intent: str, person: str) -> dict:
    memory = _load_query_memory()
    history = memory.get("history", [])
    history.append({
        "query": query,
        "rewritten": rewritten,
        "intent": intent,
        "person": person,
    })
    memory["history"] = history[-10:]
    memory["last_query"] = query
    memory["last_rewritten_query"] = rewritten
    if person:
        memory["last_person"] = person
    if intent:
        memory["last_intent"] = intent
    _save_query_memory(memory)
    return memory


def _tokenize_for_retrieval(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9+_.-]*", (text or "").lower())
    return [token for token in tokens if token not in STOPWORDS]


def _normalize_query_typos(text: str) -> str:
    normalized = re.sub(r"\s+", " ", (text or "")).strip()
    for wrong, correct in TYPO_REPLACEMENTS.items():
        normalized = re.sub(rf"\b{re.escape(wrong)}\b", correct, normalized, flags=re.IGNORECASE)
    return normalized


def _detect_person(query: str, memory: dict | None = None) -> str:
    q = (query or "").lower()
    for alias in ("abhishek", "abhishekmystic-ks", "abhi"):
        if alias in q:
            return "Abhishek"
    for alias in ("akshatha", "akshathaa"):
        if alias in q:
            return "Akshatha"
    if memory and memory.get("last_person"):
        if re.search(r"\b(his|he|him)\b", q) and memory.get("last_person") == "Abhishek":
            return "Abhishek"
        if re.search(r"\b(her|she)\b", q) and memory.get("last_person") == "Akshatha":
            return "Akshatha"
    return ""


def _rewrite_query(query: str, memory: dict | None = None) -> dict:
    memory = memory or _load_query_memory()
    raw = _normalize_query_typos(query)
    q = raw.lower()
    person = _detect_person(raw, memory)
    intent = "general"

    exact_resume_fact_terms = (
        "which company", "what company", "where did", "where has",
        "completed his internship", "completed her internship", "interned at",
    )

    if any(word in q for word in ("github", "repo", "repositories", "repository")):
        intent = "repo"
    elif "linkedin" in q or "headline" in q:
        intent = "linkedin"
    elif any(term in q for term in exact_resume_fact_terms):
        intent = "resume_fact"
    elif any(word in q for word in ("internship", "interned", "intern", "experience", "work done", "what has", "what did")):
        intent = "resume"
    elif any(word in q for word in ("resume", "cv", "education", "project", "experience", "skills", "cgpa", "gpa", "grade", "marks", "score")):
        intent = "resume"

    parts = []
    if person:
        parts.append(person)
    if intent == "repo":
        parts.extend(["github", "repositories"])
    elif intent == "linkedin":
        parts.extend(["linkedin", "profile"])
    elif intent == "resume_fact":
        parts.extend(["internship", "company"])
    elif intent == "resume":
        parts = [person, raw] if person else [raw]
    else:
        parts = [raw]

    rewritten = re.sub(r"\s+", " ", " ".join(dict.fromkeys(part for part in parts if part))).strip()
    if not rewritten:
        rewritten = raw
    return {"raw": raw, "rewritten": rewritten, "intent": intent, "person": person}


def _is_exact_resume_fact_query(query: str) -> bool:
    q = query.lower()
    return any(phrase in q for phrase in (
        "which company",
        "what company",
        "company has",
        "internship company",
        "where did",
        "where has",
        "completed his internship",
        "completed her internship",
        "interned at",
    ))


def _extract_resume_internship_details(text: str) -> dict:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("###"):
            continue
        heading = line.lstrip("# ").strip()
        if not re.search(r"intern|experience", heading, flags=re.IGNORECASE):
            continue
        match = re.match(r"(?P<role>.+?)\s+[—-]\s+(?P<company>.+)$", heading)
        if not match:
            continue
        role = re.sub(r"\s+", " ", match.group("role")).strip()
        company_raw = match.group("company").strip()
        company_raw = re.split(r",\s*", company_raw, maxsplit=1)[0].strip()
        company = _normalize_company_name(company_raw)
        return {"role": role, "company": company, "heading": heading}
    return {"role": "", "company": "", "heading": ""}


def _answer_resume_fact_query(query: str) -> str:
    files = _select_resume_files_for_query(query)
    if not files:
        return "I could not find resume knowledge files yet."

    q = query.lower()
    person = "Abhishek" if "abhishek" in q else "Akshatha" if "akshatha" in q else ""
    for path in files:
        text = path.read_text(encoding="utf-8")
        details = _extract_resume_internship_details(text)
        if not details.get("company"):
            continue
        if path.stem.lower() == "abhi_resume":
            person = person or "Abhishek"
        elif path.stem.lower() == "resume":
            person = person or "Akshatha"
        else:
            person = person or path.stem.replace("_resume", "").title()
        if details.get("role"):
            return f"{person} completed the internship at {details['company']} as {details['role']}."
        return f"{person} completed the internship at {details['company']}."

    return "I could not extract the internship company clearly from the resume files."


def _score_text(query_terms: list[str], query: str, doc: str, source: str, person: str, intent: str) -> float:
    if not doc:
        return 0.0
    doc_lower = doc.lower()
    doc_terms = set(_tokenize_for_retrieval(doc))
    query_terms = [term for term in query_terms if term]
    if not query_terms:
        query_terms = _tokenize_for_retrieval(query)
    overlap = sum(1 for term in query_terms if term in doc_terms)
    lexical = overlap / max(len(set(query_terms)), 1)
    bonus = 0.0
    if person and person.lower() in doc_lower:
        bonus += 0.15
    if intent == "resume_fact" and any(word in doc_lower for word in ("intern", "experience", "company")):
        bonus += 0.1
    if intent == "repo" and "github" in source.lower():
        bonus += 0.1
    if intent == "linkedin" and "linkedin" in source.lower():
        bonus += 0.1
    for phrase in (query.lower(), " ".join(query_terms[:3])):
        if phrase and phrase in doc_lower:
            bonus += 0.15
            break
    return lexical * 0.5 + bonus


def _load_corpus_items() -> list[dict]:
    global _corpus_cache
    if _corpus_cache is not None:
        return _corpus_cache
    collection = _get_collection()
    if collection.count() == 0:
        _corpus_cache = []
        return _corpus_cache
    data = collection.get(include=["documents", "metadatas"])
    documents = data.get("documents") or []
    metadatas = data.get("metadatas") or []
    ids = data.get("ids") or []
    items = []
    for index, doc in enumerate(documents):
        meta = metadatas[index] if index < len(metadatas) else {}
        items.append({
            "id": ids[index] if index < len(ids) else str(index),
            "doc": doc,
            "meta": meta or {},
            "source": _source_label(meta),
        })
    _corpus_cache = items
    return items


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

    if _is_exact_repo_fact_query(query):
        return _answer_repo_fact_query(query)

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


def _is_exact_repo_fact_query(query: str) -> bool:
    q = query.lower()
    return any(word in q for word in [
        "public repos", "public repositories", "followers", "location", "company",
        "profile url", "bio", "name", "how many repos", "how many repositories",
        "list all repositories", "all repositories", "repository count",
    ])


def _extract_github_profile_facts(text: str) -> dict:
    facts = {
        "name": "",
        "bio": "",
        "location": "",
        "company": "",
        "public_repos": "",
        "followers": "",
        "profile_url": "",
        "repos": [],
    }

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("Name:"):
            facts["name"] = line.split(":", 1)[1].strip()
        elif line.startswith("Bio:"):
            facts["bio"] = line.split(":", 1)[1].strip()
        elif line.startswith("Location:"):
            facts["location"] = line.split(":", 1)[1].strip()
        elif line.startswith("Company:"):
            facts["company"] = line.split(":", 1)[1].strip()
        elif line.startswith("Public repos:"):
            facts["public_repos"] = line.split(":", 1)[1].strip()
        elif line.startswith("Followers:"):
            facts["followers"] = line.split(":", 1)[1].strip()
        elif line.startswith("Profile URL:"):
            facts["profile_url"] = line.split(":", 1)[1].strip()
        elif line.startswith("-") and "| https://" in line:
            parsed = _parse_project_line(line)
            if parsed:
                facts["repos"].append(parsed)

    return facts


def _answer_repo_fact_query(query: str) -> str:
    files = _select_profile_files_for_query(query)
    if not files:
        return "I could not find GitHub profile knowledge files yet."

    q = query.lower()
    want_counts = any(word in q for word in ["public repos", "public repositories", "followers", "how many repos", "how many repositories", "repository count"])
    want_meta = any(word in q for word in ["location", "company", "profile url", "bio", "name"])
    want_list = any(word in q for word in ["repositories", "repo", "list all repositories", "all repositories"])

    lines = []
    for profile_path in files:
        facts = _extract_github_profile_facts(profile_path.read_text(encoding="utf-8"))
        person = facts.get("name") or profile_path.stem.replace("_profile", "")
        lines.append(f"GitHub facts for {person}:")

        if want_meta and facts.get("bio"):
            lines.append(f"1. Bio: {facts['bio']}")
        if want_meta and facts.get("location"):
            lines.append(f"2. Location: {facts['location']}")
        if want_meta and facts.get("company"):
            lines.append(f"3. Company: {facts['company']}")
        if want_counts and facts.get("public_repos"):
            lines.append(f"4. Public repos: {facts['public_repos']}")
        if want_counts and facts.get("followers"):
            lines.append(f"5. Followers: {facts['followers']}")
        if want_meta and facts.get("profile_url"):
            lines.append(f"6. Profile URL: {facts['profile_url']}")
        if want_list and facts.get("repos"):
            lines.append("7. Repositories:")
            for repo in facts["repos"]:
                desc = re.sub(r"\s+", " ", repo["desc"]).strip()
                lines.append(f"   - {repo['name']} - {desc}")
        lines.append("")

    if not lines:
        return "I could not extract clear GitHub profile facts from the documents."

    lines.append("These facts are extracted directly from your GitHub profile documents.")
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

    if _is_exact_linkedin_fact_query(query):
        return _answer_linkedin_fact_query(query)

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


def _is_exact_linkedin_fact_query(query: str) -> bool:
    q = query.lower()
    return any(word in q for word in [
        "location", "headline", "about", "education", "skill", "skills",
        "company", "intern", "experience", "where did", "where has", "worked at",
        "what company", "which company", "profile url", "name",
    ])


def _extract_linkedin_facts(text: str) -> dict:
    facts = {
        "name": "",
        "location": "",
        "headline": "",
        "about": "",
        "education": "",
        "experience": [],
        "skills": [],
    }

    name_match = re.search(r"^#\s+LinkedIn Profile\s+[—-]\s+(.+)$", text, flags=re.MULTILINE)
    if name_match:
        facts["name"] = name_match.group(1).strip()

    location_match = re.search(r"^(?:📍\s+|Location:\s+)(.+)$", text, flags=re.MULTILINE)
    if location_match:
        facts["location"] = location_match.group(1).strip()

    headline = _extract_section(text, "Headline")
    facts["headline"] = re.sub(r"\s+", " ", headline).strip()

    about = _extract_section(text, "About")
    facts["about"] = re.sub(r"\s+", " ", about).strip()

    education = _extract_section(text, "Education")
    facts["education"] = re.sub(r"\s+", " ", education).strip()

    experience_block = _extract_section(text, "Experience")
    for raw_line in experience_block.splitlines():
        line = raw_line.strip()
        if line.startswith("###"):
            facts["experience"].append(line.lstrip("# ").strip())

    skills_block = _extract_section(text, "Skills")
    for raw_line in skills_block.splitlines():
        line = raw_line.strip()
        if line.startswith("-"):
            facts["skills"].append(re.sub(r"\s+", " ", line[1:]).strip())

    return facts


def _answer_linkedin_fact_query(query: str) -> str:
    files = _select_linkedin_files_for_query(query)
    if not files:
        return "I could not find LinkedIn knowledge files yet."

    q = query.lower()
    want_location = "location" in q or "where" in q
    want_headline = "headline" in q
    want_about = "about" in q
    want_education = "education" in q or "study" in q
    want_skills = "skill" in q
    want_company = "company" in q or "intern" in q or "experience" in q or "worked" in q

    lines = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        facts = _extract_linkedin_facts(text)
        person = facts.get("name") or path.stem.replace("linkedin_", "").replace("_", " ").title()
        lines.append(f"LinkedIn facts for {person}:")

        if want_location and facts.get("location"):
            lines.append(f"1. Location: {facts['location']}")
        if want_headline and facts.get("headline"):
            lines.append(f"2. Headline: {facts['headline']}")
        if want_about and facts.get("about"):
            lines.append(f"3. About: {facts['about']}")
        if want_company and facts.get("experience"):
            lines.append("4. Experience:")
            for item in facts["experience"][:4]:
                lines.append(f"   - {item}")
        if want_education and facts.get("education"):
            lines.append(f"5. Education: {facts['education']}")
        if want_skills and facts.get("skills"):
            lines.append("6. Skills:")
            for skill in facts["skills"][:8]:
                lines.append(f"   - {skill}")
        lines.append("")

    if not lines:
        return "I could not extract clear LinkedIn facts from the profile documents."

    lines.append("These facts are extracted directly from your LinkedIn profile documents.")
    return "\n".join(lines)


def _is_resume_query(query: str) -> bool:
    q = _normalize_query_typos(query).lower()
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

        if line.startswith("## "):
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

    if _is_exact_resume_fact_query(query):
        return _answer_resume_fact_query(query)

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

    memory = _load_query_memory()
    query_info = _rewrite_query(query, memory)
    rewritten = query_info["rewritten"]
    person = query_info["person"]
    intent = query_info["intent"]

    embedder = get_embedder()
    query_vec = embedder.encode(rewritten).tolist()

    candidate_count = min(max(k * 4, 20), collection.count())

    results = collection.query(
        query_embeddings=[query_vec],
        n_results=candidate_count,
        include=["documents", "distances", "metadatas"],
    )

    chunks = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    ids = results.get("ids", [[]])[0]

    query_terms = _tokenize_for_retrieval(rewritten)
    scored: dict[str, dict] = {}

    for idx, (doc, dist, meta) in enumerate(zip(chunks, distances, metadatas)):
        source = _source_label(meta)
        vector_score = max(0.0, 1.0 - float(dist))
        lexical_score = _score_text(query_terms, rewritten, doc, source, person, intent)
        score = vector_score * 0.7 + lexical_score * 0.3
        key = ids[idx] if idx < len(ids) else f"vector:{idx}:{source}"
        scored[key] = {
            "doc": doc,
            "distance": dist,
            "meta": meta,
            "source": source,
            "score": score,
            "rewritten_query": rewritten,
        }

    for item in _load_corpus_items():
        source = item["source"]
        lexical_score = _score_text(query_terms, rewritten, item["doc"], source, person, intent)
        if lexical_score <= 0:
            continue
        key = item["id"]
        current = scored.get(key)
        if current and current.get("score", 0.0) >= lexical_score:
            continue
        scored[key] = {
            "doc": item["doc"],
            "distance": current["distance"] if current else 1.0 - lexical_score,
            "meta": item["meta"],
            "source": source,
            "score": lexical_score,
            "rewritten_query": rewritten,
        }

    ranked = sorted(scored.values(), key=lambda item: item.get("score", 0.0), reverse=True)
    if not ranked:
        return []

    strict = [item for item in ranked if item.get("score", 0.0) >= threshold]
    selected = strict[:k] if strict else ranked[:k]

    if strict:
        print(f"[search] hybrid search found {len(strict)} strong matches")
    else:
        print(f"[search] hybrid search using top {len(selected)} matches")

    return selected


def _build_context(items: list[dict]) -> str:
    blocks = []
    for item in items:
        blocks.append(f"Source: {item['source']}\n{item['doc']}")
    return "\n\n---\n\n".join(blocks)


def _rerank_for_synthesis(query: str, items: list[dict], limit: int = 4) -> list[dict]:
    if not items:
        return []

    query_terms = set(_tokenize_for_retrieval(query))
    scored = []
    seen_sources = set()

    for item in items:
        doc = item.get("doc", "")
        source = item.get("source", "")
        doc_terms = set(_tokenize_for_retrieval(doc))
        overlap = len(query_terms & doc_terms)
        score = float(item.get("score", 0.0))

        if overlap:
            score += overlap * 0.08
        if query_terms and any(term in doc.lower() for term in query_terms):
            score += 0.05
        if source and source not in seen_sources:
            score += 0.02
            seen_sources.add(source)

        ranked_item = dict(item)
        ranked_item["llm_rank_score"] = score
        scored.append(ranked_item)

    scored.sort(key=lambda item: item.get("llm_rank_score", 0.0), reverse=True)
    return scored[:limit]


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
            "You are a grounded RAG answer synthesizer.\n"
            "Use only the supplied context. Do not guess, infer missing facts, or add details not present in the context.\n"
            "If the context does not contain the answer, say that you could not find it in the knowledge base.\n"
            "Prefer exact facts, names, dates, locations, and counts when they appear in the context.\n"
            "Keep the answer concise, structured, and direct.\n"
            "Use this format when appropriate:\n"
            "- Short answer line\n"
            "- Numbered facts or bullets\n"
            "- One short concluding line\n\n"
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
                        "You are a grounded RAG answer synthesizer. Use only the provided context. "
                        "Do not invent facts, and if the context does not support the answer, say so clearly. "
                        "Return concise, structured answers with exact facts whenever possible."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {query}\n\n"
                        f"Context:\n{context}\n\n"
                        "Respond with a short answer, numbered facts when useful, and one-line conclusion."
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
    memory = _load_query_memory()
    query_info = _rewrite_query(query, memory)
    query_text = query_info["rewritten"] or query.strip()
    _remember_query(query, query_text, query_info["intent"], query_info["person"])

    if query_info["intent"] == "resume_fact":
        print("[search] using exact resume fact extractor...")
        return _answer_resume_fact_query(query_text)

    if _is_resume_query(query_text):
        print("[search] using direct resume parser...")
        return _answer_resume_query(query_text)

    if _is_linkedin_query(query):
        print("[search] using direct LinkedIn profile parser...")
        return _answer_linkedin_query(query)

    if _is_repo_query(query):
        print("[search] using direct GitHub repository parser...")
        return _answer_repo_query(query)

    print("[search] retrieving relevant chunks with hybrid search...")
    items = _search(query_text, k=k, threshold=threshold)
    if not items:
        return "I could not find relevant data in the knowledge base."

    llm_items = _rerank_for_synthesis(query_text, items, limit=min(4, len(items)))

    print("[understand] building context and synthesizing answer...")
    context = _build_context(llm_items)
    llm_answer = _llm_explain(query, context)
    if llm_answer:
        print("[explain] generated final answer")
        return llm_answer

    print("[explain] llm unavailable, using fallback explainer")
    return _fallback_explain(query, llm_items)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else "what projects has Akshatha built"
    result = answer_query(query)
    print("\n=== ANSWER ===")
    print(result if result else "(nothing found)")