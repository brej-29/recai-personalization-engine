# XM ablation

Mode: test

## bge-small

| System | NDCG@10 | 95% CI |
|---|---:|---:|
| random | 0.0039 | [0.0027, 0.0052] |
| popularity | 0.0294 | [0.0249, 0.0341] |
| genre | 0.0802 | [0.0721, 0.0885] |
| tag_tfidf | 0.1422 | [0.1311, 0.1537] |
| description_tfidf | 0.0951 | [0.0861, 0.1044] |
| zero_shot | 0.0824 | [0.0738, 0.0915] |
| centering | 0.0909 | [0.0817, 0.1005] |
| adapter | 0.1211 | [0.1105, 0.1317] |
| adapter+centering | 0.0929 | [0.0835, 0.1025] |
| fusion | 0.2083 | [0.1951, 0.2215] |
| fusion-no-pop | 0.1836 | [0.1708, 0.1967] |
| fusion-no-tag | 0.1471 | [0.1359, 0.1585] |

Popularity top-decile share (system vs ground truth):
ground truth: 0.1213
random: 0.0473
popularity: 0.5786
genre: 0.1141
tag_tfidf: 0.0467
description_tfidf: 0.0554
zero_shot: 0.0461
centering: 0.0439
adapter: 0.0516
adapter+centering: 0.0508
fusion: 0.3016
fusion-no-pop: 0.0554
fusion-no-tag: 0.3759

NDCG@10 by direction (full detail in xm.json):

| System | anime->print | print->anime |
|---|---:|---:|
| random | 0.0027 | 0.0052 |
| popularity | 0.0329 | 0.0254 |
| genre | 0.0856 | 0.0743 |
| tag_tfidf | 0.1266 | 0.1596 |
| description_tfidf | 0.0822 | 0.1095 |
| zero_shot | 0.0745 | 0.0912 |
| centering | 0.0793 | 0.1039 |
| adapter | 0.1197 | 0.1226 |
| adapter+centering | 0.0781 | 0.1094 |
| fusion | 0.2072 | 0.2094 |
| fusion-no-pop | 0.1819 | 0.1854 |
| fusion-no-tag | 0.1488 | 0.1451 |

## gte-small

| System | NDCG@10 | 95% CI |
|---|---:|---:|
| random | 0.0039 | [0.0027, 0.0052] |
| popularity | 0.0294 | [0.0249, 0.0341] |
| genre | 0.0802 | [0.0721, 0.0885] |
| tag_tfidf | 0.1422 | [0.1311, 0.1537] |
| description_tfidf | 0.0951 | [0.0861, 0.1044] |
| zero_shot | 0.1212 | [0.1109, 0.1317] |
| centering | 0.1199 | [0.1094, 0.1308] |
| adapter | 0.1410 | [0.1301, 0.1521] |
| adapter+centering | 0.1085 | [0.0984, 0.1190] |
| fusion | 0.2172 | [0.2033, 0.2308] |
| fusion-no-pop | 0.1867 | [0.1736, 0.1997] |
| fusion-no-tag | 0.1635 | [0.1516, 0.1752] |

Popularity top-decile share (system vs ground truth):
ground truth: 0.1213
random: 0.0473
popularity: 0.5786
genre: 0.1141
tag_tfidf: 0.0467
description_tfidf: 0.0554
zero_shot: 0.0500
centering: 0.0491
adapter: 0.0498
adapter+centering: 0.0514
fusion: 0.2901
fusion-no-pop: 0.0536
fusion-no-tag: 0.3690

NDCG@10 by direction (full detail in xm.json):

| System | anime->print | print->anime |
|---|---:|---:|
| random | 0.0027 | 0.0052 |
| popularity | 0.0329 | 0.0254 |
| genre | 0.0856 | 0.0743 |
| tag_tfidf | 0.1266 | 0.1596 |
| description_tfidf | 0.0822 | 0.1095 |
| zero_shot | 0.1028 | 0.1417 |
| centering | 0.0958 | 0.1467 |
| adapter | 0.1360 | 0.1465 |
| adapter+centering | 0.0849 | 0.1348 |
| fusion | 0.2129 | 0.2219 |
| fusion-no-pop | 0.1752 | 0.1995 |
| fusion-no-tag | 0.1629 | 0.1642 |

## minilm

| System | NDCG@10 | 95% CI |
|---|---:|---:|
| random | 0.0039 | [0.0027, 0.0052] |
| popularity | 0.0294 | [0.0249, 0.0341] |
| genre | 0.0802 | [0.0721, 0.0885] |
| tag_tfidf | 0.1422 | [0.1311, 0.1537] |
| description_tfidf | 0.0951 | [0.0861, 0.1044] |
| zero_shot | 0.0722 | [0.0643, 0.0803] |
| centering | 0.0772 | [0.0689, 0.0860] |
| adapter | 0.0948 | [0.0854, 0.1045] |
| adapter+centering | 0.0754 | [0.0666, 0.0844] |
| fusion | 0.1847 | [0.1721, 0.1972] |
| fusion-no-pop | 0.1799 | [0.1673, 0.1923] |
| fusion-no-tag | 0.0986 | [0.0895, 0.1075] |

Popularity top-decile share (system vs ground truth):
ground truth: 0.1213
random: 0.0473
popularity: 0.5786
genre: 0.1141
tag_tfidf: 0.0467
description_tfidf: 0.0554
zero_shot: 0.0490
centering: 0.0501
adapter: 0.0511
adapter+centering: 0.0472
fusion: 0.3980
fusion-no-pop: 0.0524
fusion-no-tag: 0.5097

NDCG@10 by direction (full detail in xm.json):

| System | anime->print | print->anime |
|---|---:|---:|
| random | 0.0027 | 0.0052 |
| popularity | 0.0329 | 0.0254 |
| genre | 0.0856 | 0.0743 |
| tag_tfidf | 0.1266 | 0.1596 |
| description_tfidf | 0.0822 | 0.1095 |
| zero_shot | 0.0717 | 0.0729 |
| centering | 0.0719 | 0.0832 |
| adapter | 0.0909 | 0.0992 |
| adapter+centering | 0.0637 | 0.0884 |
| fusion | 0.1935 | 0.1749 |
| fusion-no-pop | 0.1679 | 0.1932 |
| fusion-no-tag | 0.1053 | 0.0912 |

## qwen3-0.6b

| System | NDCG@10 | 95% CI |
|---|---:|---:|
| random | 0.0039 | [0.0027, 0.0052] |
| popularity | 0.0294 | [0.0249, 0.0341] |
| genre | 0.0802 | [0.0721, 0.0885] |
| tag_tfidf | 0.1422 | [0.1311, 0.1537] |
| description_tfidf | 0.0951 | [0.0861, 0.1044] |
| zero_shot | 0.1079 | [0.0981, 0.1182] |
| centering | 0.1029 | [0.0932, 0.1132] |
| adapter | 0.1437 | [0.1320, 0.1556] |
| adapter+centering | 0.1099 | [0.0996, 0.1206] |
| fusion | 0.2297 | [0.2158, 0.2437] |
| fusion-no-pop | 0.1944 | [0.1812, 0.2079] |
| fusion-no-tag | 0.1707 | [0.1585, 0.1831] |

Popularity top-decile share (system vs ground truth):
ground truth: 0.1213
random: 0.0473
popularity: 0.5786
genre: 0.1141
tag_tfidf: 0.0467
description_tfidf: 0.0554
zero_shot: 0.0517
centering: 0.0504
adapter: 0.0445
adapter+centering: 0.0524
fusion: 0.2681
fusion-no-pop: 0.0524
fusion-no-tag: 0.3345

NDCG@10 by direction (full detail in xm.json):

| System | anime->print | print->anime |
|---|---:|---:|
| random | 0.0027 | 0.0052 |
| popularity | 0.0329 | 0.0254 |
| genre | 0.0856 | 0.0743 |
| tag_tfidf | 0.1266 | 0.1596 |
| description_tfidf | 0.0822 | 0.1095 |
| zero_shot | 0.0859 | 0.1325 |
| centering | 0.0788 | 0.1298 |
| adapter | 0.1299 | 0.1592 |
| adapter+centering | 0.0813 | 0.1417 |
| fusion | 0.2260 | 0.2338 |
| fusion-no-pop | 0.1748 | 0.2163 |
| fusion-no-tag | 0.1678 | 0.1739 |
