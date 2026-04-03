# 생명과학 고전(1970~1999) 키워드 선정

## 담당자: 김승환
## 작성일: 2026-04-03

---

## 1. Semantic Scholar 검색 전략

### 1.1 Fields of Study (1차 필터)

Semantic Scholar API의 `fieldsOfStudy` 파라미터 사용:

```python
FIELDS_OF_STUDY = [
    "Biology",
    "Biochemistry",
    "Molecular Biology",
    "Cell Biology",
    "Genetics",
    "Ecology",
    "Microbiology",
    "Evolutionary Biology",
    "Neuroscience",      # 기초 신경과학만, 임상 제외
    "Botany",
    "Zoology",
]
```

---

## 2. 세부 키워드 (2차 필터 또는 검색어)

### 2.1 분자생물학 (Molecular Biology)

```python
MOLECULAR_BIOLOGY = [
    # DNA/RNA
    "DNA replication", "transcription", "translation",
    "gene expression", "gene regulation", "operon",
    "promoter", "enhancer", "ribosome",
    "messenger RNA", "transfer RNA", "ribosomal RNA",

    # 분자 기술
    "recombinant DNA", "restriction enzyme", "plasmid",
    "cloning", "Southern blot", "Northern blot",
    "polymerase chain reaction", "PCR", "gel electrophoresis",
    "DNA sequencing", "Sanger sequencing",

    # 단백질
    "protein structure", "protein folding", "enzyme kinetics",
    "protein synthesis", "amino acid sequence",
]
```

### 2.2 세포생물학 (Cell Biology)

```python
CELL_BIOLOGY = [
    # 세포 구조
    "cell membrane", "cytoplasm", "nucleus",
    "mitochondria", "endoplasmic reticulum", "Golgi apparatus",
    "lysosome", "cytoskeleton", "organelle",

    # 세포 과정
    "cell cycle", "mitosis", "meiosis",
    "cell division", "apoptosis", "programmed cell death",
    "cell signaling", "signal transduction",
    "endocytosis", "exocytosis", "cell adhesion",

    # 세포 유형
    "stem cell", "differentiation", "cell culture",
]
```

### 2.3 유전학 (Genetics)

```python
GENETICS = [
    # 고전 유전학
    "Mendelian inheritance", "allele", "genotype", "phenotype",
    "dominant", "recessive", "chromosome", "mutation",
    "genetic mapping", "linkage", "recombination",

    # 분자 유전학
    "genome", "genetic code", "codon", "anticodon",
    "gene mutation", "point mutation", "deletion", "insertion",
    "transposon", "mobile genetic element",

    # 집단 유전학
    "population genetics", "genetic drift", "gene flow",
    "Hardy-Weinberg", "natural selection", "fitness",
]
```

### 2.4 생화학 (Biochemistry)

```python
BIOCHEMISTRY = [
    # 대사
    "metabolism", "glycolysis", "citric acid cycle",
    "oxidative phosphorylation", "ATP synthesis",
    "photosynthesis", "Calvin cycle", "electron transport chain",

    # 효소
    "enzyme", "catalysis", "Michaelis-Menten",
    "enzyme inhibition", "allosteric regulation",
    "coenzyme", "cofactor",

    # 생체분자
    "lipid", "carbohydrate", "nucleotide",
    "amino acid", "protein", "nucleic acid",
]
```

### 2.5 미생물학 (Microbiology)

```python
MICROBIOLOGY = [
    # 미생물 종류
    "bacteria", "bacterium", "archaea",
    "virus", "bacteriophage", "fungi", "yeast",

    # 미생물 생리
    "bacterial growth", "microbial metabolism",
    "antibiotic resistance", "plasmid transfer",
    "biofilm", "quorum sensing",

    # 기술
    "bacterial culture", "fermentation",
    "microbiome", "microbial ecology",
]
```

### 2.6 진화생물학 (Evolutionary Biology)

```python
EVOLUTIONARY_BIOLOGY = [
    # 진화 메커니즘
    "natural selection", "evolution", "adaptation",
    "speciation", "phylogeny", "phylogenetic",
    "molecular evolution", "genetic variation",

    # 진화 증거
    "fossil record", "comparative anatomy",
    "homology", "analogy", "convergent evolution",

    # 분자 진화
    "molecular clock", "sequence alignment",
    "evolutionary tree", "common ancestor",
]
```

### 2.7 생태학 (Ecology)

```python
ECOLOGY = [
    # 생태계
    "ecosystem", "food chain", "food web",
    "trophic level", "energy flow", "nutrient cycle",
    "carbon cycle", "nitrogen cycle",

    # 개체군/군집
    "population dynamics", "carrying capacity",
    "predator-prey", "competition", "symbiosis",
    "mutualism", "parasitism", "community ecology",

    # 환경
    "habitat", "niche", "biodiversity",
    "conservation", "endangered species",
]
```

### 2.8 발생생물학 (Developmental Biology)

```python
DEVELOPMENTAL_BIOLOGY = [
    # 발생 과정
    "embryo", "embryogenesis", "gastrulation",
    "morphogenesis", "organogenesis", "differentiation",

    # 조절
    "developmental gene", "homeotic gene", "Hox gene",
    "pattern formation", "axis formation",
    "growth factor", "cell fate",

    # 모델 생물
    "Drosophila", "C. elegans", "Xenopus",
    "zebrafish", "mouse embryo",
]
```

### 2.9 신경과학 (Neuroscience) - 기초만

```python
NEUROSCIENCE_BASIC = [
    # 신경 세포
    "neuron", "synapse", "axon", "dendrite",
    "action potential", "neurotransmitter",
    "ion channel", "membrane potential",

    # 신경 회로
    "neural circuit", "neural network",
    "synaptic plasticity", "long-term potentiation",

    # 감각/인지 (기초)
    "sensory neuron", "motor neuron",
    "visual cortex", "auditory system",
]
```

### 2.10 식물생물학 (Plant Biology)

```python
PLANT_BIOLOGY = [
    # 식물 생리
    "photosynthesis", "chloroplast", "chlorophyll",
    "plant hormone", "auxin", "gibberellin", "cytokinin",
    "stomata", "transpiration",

    # 식물 발생
    "seed germination", "root development",
    "flower development", "fruit development",

    # 식물 분자생물학
    "plant cell wall", "plastid", "plant genome",
]
```

---

## 3. 제외 키워드 (medicine/healthcare)

```python
EXCLUDE_KEYWORDS = [
    # 임상 관련
    "clinical", "clinical trial", "patient", "patients",
    "diagnosis", "prognosis", "treatment", "therapy",
    "surgery", "surgical", "hospital", "physician",
    "medical practice", "healthcare",

    # 질병 관련 (임상적 맥락)
    "disease treatment", "disease management",
    "therapeutic", "therapeutics",

    # 약물 관련
    "drug therapy", "drug treatment", "pharmaceutical",
    "medication", "dosage", "pharmacotherapy",
    "drug delivery", "drug design",

    # 의료 기기/시술
    "medical device", "implant", "prosthetic",
    "imaging diagnosis", "MRI diagnosis", "CT scan",
]
```

### 주의: 제외하지 말아야 할 키워드

아래는 기초 연구에서 자주 사용되므로 **제외하지 않음**:

```python
KEEP_KEYWORDS = [
    "disease model",      # 질병 모델 (기초 연구)
    "cancer cell",        # 암세포 (세포생물학 연구)
    "tumor cell line",    # 종양 세포주 (기초 연구)
    "drug resistance",    # 약물 저항성 (분자생물학)
    "pathogen",           # 병원체 (미생물학)
    "infection mechanism",# 감염 메커니즘 (기초 연구)
]
```

---

## 4. Semantic Scholar 쿼리 전략

### 4.1 기본 쿼리 구조

```python
# 방법 1: fieldsOfStudy 필터 사용
query_params = {
    "query": "",  # 빈 쿼리로 전체 검색
    "fieldsOfStudy": "Biology",
    "year": "1970-1999",
    "limit": 100,
    "fields": "title,abstract,authors,year,citationCount,fieldsOfStudy,publicationTypes"
}

# 방법 2: 키워드 검색
query_params = {
    "query": "molecular biology gene expression",
    "year": "1970-1999",
    "limit": 100,
    "fields": "..."
}
```

### 4.2 수집 우선순위

| 우선순위 | 분야 | 예상 논문 수 | 비고 |
|---------|------|-------------|------|
| 1 | Molecular Biology | 높음 | 1970~1990년대 황금기 |
| 2 | Cell Biology | 높음 | |
| 3 | Genetics | 높음 | Human Genome Project 전 연구들 |
| 4 | Biochemistry | 중간 | |
| 5 | Microbiology | 중간 | |
| 6 | Evolutionary Biology | 중간 | |
| 7 | Developmental Biology | 중간 | |
| 8 | Ecology | 중간 | |
| 9 | Neuroscience (기초) | 낮음 | 임상 제외 주의 |
| 10 | Plant Biology | 낮음 | |

---

## 5. 1970~1999 생명과학 주요 연구 토픽 (시대별)

### 5.1 1970년대
- 재조합 DNA 기술 발명 (1973)
- DNA 시퀀싱 방법 개발 (Sanger, 1977)
- 분자 클로닝 기술

### 5.2 1980년대
- PCR 발명 (1983)
- Transgenic 동물
- Oncogene 발견
- Cell cycle 연구

### 5.3 1990년대
- Human Genome Project 시작 (1990)
- RNA interference 발견
- Stem cell 연구
- Bioinformatics 태동

---

## 6. 최종 키워드 리스트 (Python 형식)

```python
BIOLOGY_KEYWORDS = {
    "fields_of_study": [
        "Biology", "Biochemistry", "Molecular Biology",
        "Cell Biology", "Genetics", "Ecology",
        "Microbiology", "Evolutionary Biology",
        "Neuroscience", "Botany", "Zoology"
    ],

    "search_queries": [
        # Tier 1: 핵심 키워드
        "molecular biology",
        "cell biology",
        "genetics gene",
        "biochemistry enzyme",
        "DNA RNA protein",

        # Tier 2: 세부 키워드
        "gene expression regulation",
        "protein structure function",
        "cell cycle division",
        "evolution phylogeny",
        "microbiology bacteria",
        "ecology ecosystem",
        "developmental biology embryo",
        "neuron synapse neuroscience",
        "plant photosynthesis",
    ],

    "exclude_patterns": [
        r"\bclinical\s+trial",
        r"\bpatient[s]?\b",
        r"\btherapy\b",
        r"\btreatment\b",
        r"\bsurgery\b",
        r"\bhospital\b",
        r"\bpharmaceutical\b",
        r"\bdrug\s+(therapy|treatment|delivery)\b",
    ],

    "year_range": (1970, 1999),
}
```

---

## 7. 예상 수집 규모

| 분야 | 예상 논문 수 | Full-text 예상 |
|------|-------------|---------------|
| Molecular Biology | 50,000+ | 5,000~10,000 |
| Cell Biology | 40,000+ | 4,000~8,000 |
| Genetics | 40,000+ | 4,000~8,000 |
| Biochemistry | 30,000+ | 3,000~6,000 |
| 기타 | 40,000+ | 4,000~8,000 |
| **합계** | **200,000+** | **20,000~40,000** |

> **참고**: Full-text 확보율은 약 10~20%로 예상 (Open Access 논문 위주)
