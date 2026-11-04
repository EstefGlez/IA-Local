"""Tests comparativos: MemoryStore (nuevo, POO) vs implementación original (funcional).

Comportamiento idéntico requerido: misma entrada -> misma salida en ambas implementaciones.
Cada implementación escribe en su propia carpeta temporal para aislar completamente.
"""

import json
import os
import re
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.memory_store import MemoryStore
import tests._old_memory_impl as old


def _make_temp_dir():
    return Path(tempfile.mkdtemp(prefix="ia_mem_test_"))


def _cleanup(paths):
    for p in paths:
        shutil.rmtree(p, ignore_errors=True)


# Casos de detect_json_memory_proposal (6 textos requeridos)
_CASE_VALID_JSON_BLOCK = """```json
{
    "filename": "memoria_2026.json",
    "content": {"tema": "prueba", "resumen": "algo"},
    "topic_summary": "tema de prueba"
}
```"""

_CASE_INLINE_JSON = '{"filename": "inline.json", "content": {"key": "value"}, "topic_summary": "resumen inline"}'

_CASE_MISSING_FIELDS = '{"filename": "x.json", "content": {}}'

_CASE_BROKEN_JSON = """```json
{filename: no comillas, content: roto}
```"""

_CASE_NO_JSON = "Este es un texto normal sin ningun JSON."

_CASE_ACCENTS = """```json
{
    "filename": "memoria_español.json",
    "content": {"tema": "café", "resumen": "niño", "extra": "año ¿qué?"},
    "topic_summary": "tema con acentos y eñe"
}
```"""


def _equal(a, b):
    if a is None or b is None:
        return a is None and b is None
    return a == b


def _strip_saved_at(data):
    """Devuelve una copia del dict sin metadata.saved_at para comparar contenido."""
    if not isinstance(data, dict):
        return data
    result = json.loads(json.dumps(data))
    meta = result.get("metadata")
    if isinstance(meta, dict):
        meta.pop("saved_at", None)
    return result


# ============================================================
# 1. Comparacion de patrones regex (caracter a caracter)
# ============================================================

def test_regex_patterns_identical():
    """Los 3 patrones regex de detect_json_memory_proposal deben ser identicos."""
    import inspect

    new_src = inspect.getsource(MemoryStore.detect_json_memory_proposal)
    old_src = inspect.getsource(old.detect_json_memory_proposal)

    def extract(source):
        pats = {}
        for name in ("json_blocks", "inline_json_pattern", "simple_pattern"):
            m = re.search(rf'{name}\s*=\s*(?:re\.findall\()?r\'([^\']*)\'', source)
            pats[name] = m.group(1) if m else None
        return pats

    new_pats = extract(new_src)
    old_pats = extract(old_src)

    for name in ("json_blocks", "inline_json_pattern", "simple_pattern"):
        assert new_pats[name] is not None, (
            f"Patron '{name}' no encontrado en MemoryStore.detect_json_memory_proposal"
        )
        assert old_pats[name] is not None, (
            f"Patron '{name}' no encontrado en old.detect_json_memory_proposal"
        )

    assert new_pats == old_pats, (
        f"Patrones regex difieren:\n  Nuevo: {new_pats}\n  Viejo: {old_pats}"
    )


# ============================================================
# 2. detect_json_memory_proposal: 6 casos
# ============================================================

def test_detect_valid_json_block():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        r_new = store.detect_json_memory_proposal(_CASE_VALID_JSON_BLOCK)
        r_old = old.detect_json_memory_proposal(_CASE_VALID_JSON_BLOCK)
        assert _equal(r_new, r_old)
        assert r_new is not None
        assert r_new["filename"] == "memoria_2026.json"
    finally:
        _cleanup([tmp_new, tmp_old])


def test_detect_inline_json():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        r_new = store.detect_json_memory_proposal(_CASE_INLINE_JSON)
        r_old = old.detect_json_memory_proposal(_CASE_INLINE_JSON)
        assert _equal(r_new, r_old)
        assert r_new is not None
    finally:
        _cleanup([tmp_new, tmp_old])


def test_detect_missing_fields():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        r_new = store.detect_json_memory_proposal(_CASE_MISSING_FIELDS)
        r_old = old.detect_json_memory_proposal(_CASE_MISSING_FIELDS)
        assert _equal(r_new, r_old)
        assert r_new is None
    finally:
        _cleanup([tmp_new, tmp_old])


def test_detect_broken_json():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        r_new = store.detect_json_memory_proposal(_CASE_BROKEN_JSON)
        r_old = old.detect_json_memory_proposal(_CASE_BROKEN_JSON)
        assert _equal(r_new, r_old)
        assert r_new is None
    finally:
        _cleanup([tmp_new, tmp_old])


def test_detect_no_json():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        r_new = store.detect_json_memory_proposal(_CASE_NO_JSON)
        r_old = old.detect_json_memory_proposal(_CASE_NO_JSON)
        assert _equal(r_new, r_old)
        assert r_new is None
    finally:
        _cleanup([tmp_new, tmp_old])


def test_detect_accents():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        r_new = store.detect_json_memory_proposal(_CASE_ACCENTS)
        r_old = old.detect_json_memory_proposal(_CASE_ACCENTS)
        assert _equal(r_new, r_old)
        assert r_new is not None
        assert r_new["filename"] == "memoria_español.json"
        assert r_new["content"]["tema"] == "café"
    finally:
        _cleanup([tmp_new, tmp_old])


# ============================================================
# 3. Comparacion de comportamiento de las 8 funciones
# ============================================================

def _setup_pair():
    tmp_new = _make_temp_dir()
    tmp_old = _make_temp_dir()
    old.memory_base_dir = tmp_old
    store = MemoryStore(base_dir=str(tmp_new))
    return tmp_new, tmp_old, store


def test_get_memory_dir():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        sid = "sess_1"
        assert store.get_memory_dir(sid) == tmp_new / sid
        assert old.get_memory_dir(sid) == tmp_old / sid
    finally:
        _cleanup([tmp_new, tmp_old])


def test_save_and_load_memory_file():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        sid = "sess_2"
        fname = "a.json"
        data = {
            "metadata": {"saved_at": "2026-01-01"},
            "content": {"tema": "café", "resumen": "niño año ¿qué?"},
        }
        assert store.save_memory_file(sid, fname, data) is True
        assert old.save_memory_file(sid, fname, data) is True

        # Texto crudo de los dos archivos debe ser identico carácter por carácter
        raw_new = (tmp_new / sid / fname).read_text(encoding="utf-8")
        raw_old = (tmp_old / sid / fname).read_text(encoding="utf-8")
        assert raw_new == raw_old, (
            f"Textos crudos difieren:\nNUEVO:\n{raw_new}\nVIEJO:\n{raw_old}"
        )

        # Verificar acentos literales en disco (ensure_ascii=False)
        assert "café" in raw_new
        assert "\\u00e9" not in raw_new

        assert store.load_memory_file(sid, fname) == data
        assert old.load_memory_file(sid, fname) == data
    finally:
        _cleanup([tmp_new, tmp_old])


def test_list_memory_files():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        sid = "sess_3"
        store.save_memory_file(sid, "a.json", {})
        store.save_memory_file(sid, "b.json", {})
        old.save_memory_file(sid, "a.json", {})
        old.save_memory_file(sid, "b.json", {})
        new_names = sorted(f.name for f in store.list_memory_files(sid))
        old_names = sorted(f.name for f in old.list_memory_files(sid))
        assert new_names == old_names == ["a.json", "b.json"]
    finally:
        _cleanup([tmp_new, tmp_old])


def test_list_memory_files_nonexistent_session():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        assert store.list_memory_files("no_existe_sesion") == []
        assert old.list_memory_files("no_existe_sesion") == []
    finally:
        _cleanup([tmp_new, tmp_old])


def test_delete_memory_file():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        sid = "sess_4"
        fname = "del.json"
        store.save_memory_file(sid, fname, {})
        old.save_memory_file(sid, fname, {})
        assert store.delete_memory_file(sid, fname) is True
        assert old.delete_memory_file(sid, fname) is True
        assert store.load_memory_file(sid, fname) == {}
        assert old.load_memory_file(sid, fname) == {}
    finally:
        _cleanup([tmp_new, tmp_old])


def test_delete_last_file_removes_session_folder():
    """Al borrar el ultimo archivo de una sesion, la carpeta de la sesion desaparece en ambas."""
    tmp_new, tmp_old, store = _setup_pair()
    try:
        sid = "sess_5"
        fname = "unico.json"
        store.save_memory_file(sid, fname, {})
        old.save_memory_file(sid, fname, {})

        assert (tmp_new / sid).exists()
        assert (tmp_old / sid).exists()

        assert store.delete_memory_file(sid, fname) is True
        assert old.delete_memory_file(sid, fname) is True

        assert not (tmp_new / sid).exists(), (
            f"La carpeta nueva de sesion {sid} deberia haberse eliminado"
        )
        assert not (tmp_old / sid).exists(), (
            f"La carpeta vieja de sesion {sid} deberia haberse eliminado"
        )
    finally:
        _cleanup([tmp_new, tmp_old])


def test_list_all_sessions_with_memory():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        for ses in ("sa", "sb", "sc"):
            store.save_memory_file(ses, "a.json", {})
            old.save_memory_file(ses, "a.json", {})

        # Comparar SIN ordenar: ambas deben devolver orden descendente ["sc", "sb", "sa"]
        new_result = store.list_all_sessions_with_memory()
        old_result = old.list_all_sessions_with_memory()
        assert new_result == old_result
        assert new_result == ["sc", "sb", "sa"], (
            f"Orden descendente incorrecto: {new_result}"
        )
    finally:
        _cleanup([tmp_new, tmp_old])


def test_save_memory_from_proposal_legacy():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        sid = "sess_6"
        fname = "leg.json"
        proposal = {"filename": fname, "content": {"tema": "legado"}, "topic_summary": "tema legado"}
        ok_new, msg_new = store.save_memory_from_proposal(sid, proposal)
        ok_old, msg_old = old.save_memory_from_proposal(sid, proposal)
        assert ok_new == ok_old is True
        assert msg_new == msg_old
        assert "guardado correctamente" in msg_new

        # Comparar contenido JSON ignorando solo metadata.saved_at
        new_data = json.loads((tmp_new / sid / fname).read_text(encoding="utf-8"))
        old_data = json.loads((tmp_old / sid / fname).read_text(encoding="utf-8"))
        assert _strip_saved_at(new_data) == _strip_saved_at(old_data)
    finally:
        _cleanup([tmp_new, tmp_old])


def test_save_memory_from_proposal_memory_data():
    tmp_new, tmp_old, store = _setup_pair()
    try:
        sid = "sess_7"
        fname = "md.json"
        proposal = {
            "memory_data": {
                "metadata": {"filename": fname, "session_id": sid, "topic": "tema md"},
                "content": {"clave": "valor"},
            }
        }
        ok_new, msg_new = store.save_memory_from_proposal(sid, proposal)
        ok_old, msg_old = old.save_memory_from_proposal(sid, proposal)
        assert ok_new == ok_old is True

        new_data = json.loads((tmp_new / sid / fname).read_text(encoding="utf-8"))
        old_data = json.loads((tmp_old / sid / fname).read_text(encoding="utf-8"))
        assert new_data == old_data
        assert new_data["content"]["clave"] == "valor"
    finally:
        _cleanup([tmp_new, tmp_old])


def test_save_memory_from_proposal_sin_filename():
    """Propuesta sin filename debe devolver (False, mensaje) igual en ambas implementaciones."""
    tmp_new, tmp_old, store = _setup_pair()
    try:
        sid = "sess_8"
        proposal = {"content": {"a": 1}}
        ok_new, msg_new = store.save_memory_from_proposal(sid, proposal)
        ok_old, msg_old = old.save_memory_from_proposal(sid, proposal)
        assert ok_new == ok_old is False
        assert msg_new == msg_old == "Propuesta incompleta: faltan filename o content"
    finally:
        _cleanup([tmp_new, tmp_old])


if __name__ == "__main__":
    all_tests = [
        test_regex_patterns_identical,
        test_detect_valid_json_block,
        test_detect_inline_json,
        test_detect_missing_fields,
        test_detect_broken_json,
        test_detect_no_json,
        test_detect_accents,
        test_get_memory_dir,
        test_save_and_load_memory_file,
        test_list_memory_files,
        test_list_memory_files_nonexistent_session,
        test_delete_memory_file,
        test_delete_last_file_removes_session_folder,
        test_list_all_sessions_with_memory,
        test_save_memory_from_proposal_legacy,
        test_save_memory_from_proposal_memory_data,
        test_save_memory_from_proposal_sin_filename,
    ]
    passed = failed = 0
    for fn in all_tests:
        try:
            fn()
            print(f"PASS: {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{'=' * 50}")
    print(f"Resultado: {passed} passed, {failed} failed de {len(all_tests)}")
    sys.exit(1 if failed else 0)
