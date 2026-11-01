import numpy as np

from kindred.export_web import MEDIA, dequant, reference_recommend


def toy():
    # 5 titles: 0 and 1 share a franchise; media 0,0,2,6,7
    emb = np.array([[1, 0], [0.98, 0.2], [0.8, 0.6], [0.6, 0.8], [0, 1]], dtype=np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    cat = {"f": [1, 1, 2, 3, 4], "m": [0, 0, 2, 6, 7]}
    indptr = np.zeros(6, dtype=np.uint32)
    return emb, indptr, np.zeros(0, dtype=np.uint16), np.zeros(0, dtype=np.float16), np.zeros(5, dtype=np.float16), cat


def test_reference_hides_franchise_and_orders_by_score():
    emb, ptr, idx, val, pz, cat = toy()
    idx = np.array([0], dtype=np.uint16)  # keep max(indices) valid
    got = reference_recommend(emb, ptr, idx, val, pz, cat, {"a": 1, "b": 0, "c": 0}, [0], None, True, 5)
    assert got == [2, 3, 4]


def test_reference_gives_every_shelf_a_slot_before_filling():
    emb, ptr, idx, val, pz, cat = toy()
    idx = np.array([0], dtype=np.uint16)
    got = reference_recommend(emb, ptr, idx, val, pz, cat, {"a": 1, "b": 0, "c": 0}, [4], None, False, 3)
    assert len(got) == 3 and {cat["m"][i] for i in got} == {0, 2, 6}


def test_dequant_roundtrip_is_close():
    v = np.array([[0.5, -0.5, 1.0]], dtype=np.float32)
    q = np.round(v * 127).astype(np.int8)
    assert np.allclose(dequant(q), v, atol=1 / 127)


def test_media_order_matches_the_web_app():
    assert MEDIA == ["anime", "anime-film", "manga", "manhwa", "manhua", "novel", "movie", "series"]
