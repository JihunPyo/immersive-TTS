# immersive-TTS

텍스트를 넣으면 등장인물마다 다른 목소리로 읽어주는 TTS. 캡스톤 프로젝트다.
설계와 결정 사항은 `docs/시스템설계.md`가 기준이다. claude.ai 원본 문서보다 이 파일이 최신이다.

## 작업 방식

- 사용자는 개발 과정에 직접 참여하며 배우고 싶어 한다. 한 번에 한 단계씩 진행한다.
- Claude가 단계별 코드를 작성하고 설명한다 → 사용자가 직접 실행해 본다 → 확인되면 다음 단계로 간다.
- 새 라이브러리나 개념은 처음 쓸 때 왜 필요한지 짧게 설명한다.
- 설계를 바꾸는 결정은 사용자가 내린다. 결정되면 `docs/시스템설계.md`에 반영한다.
- 답변과 문서, 코드 주석은 한국어로 쓴다. 식별자는 영어.

## 두 컴퓨터

같은 레포를 두 곳에서 쓴다. 작업 시작 전에 `hostname`으로 어느 쪽인지 확인한다.

| | 맥북 (개발) | 연구실 서버 `gpusystem` (학습) |
| --- | --- | --- |
| 용도 | 코드 작성, 데이터 살펴보기, CPU 추론·벤치마크 | 모델 학습, 대량 데이터 전처리 |
| 경로 | `~/Dev/immersive-TTS` | `/home/pjh7639/immersive-TTS` |
| 하드웨어 | Apple Silicon (arm64), MPS | RTX 4090 24GB × 8 (공용) |
| conda | `/opt/anaconda3` | `/opt/miniconda3`, env는 `~/.conda/envs` |

### 코드는 git, 데이터와 모델은 rsync

- 코드, 설정, 문서만 GitHub(`JihunPyo/immersive-TTS`, `main` 브랜치)로 주고받는다.
- 작업 시작: `git pull`. 다른 컴퓨터로 옮기기 전: 커밋 후 `git push`.
- 두 곳에서 동시에 같은 파일을 고치지 않는다. 충돌이 나면 사용자에게 먼저 알린다.
- 커밋과 푸시는 사용자가 요청할 때만 한다. 세션을 마칠 때 푸시 안 된 커밋이 있으면 알려 준다.
- 서버의 remote는 HTTPS(`https://github.com/...`)다. 연구실 방화벽 때문에 서버에서 GitHub SSH가 막힌 적이 있다. 맥북은 SSH 그대로.
- `data/`, `models/`, 학습 로그·체크포인트는 git에 넣지 않는다(`.gitignore`). 옮길 때는 맥북 터미널에서 scp를 쓴다. 서버에 rsync가 없다.
  ```bash
  # 맥북 → 서버: 원본 데이터 보내기 (<서버>는 맥북 ~/.ssh/config의 호스트 이름)
  scp -r "data/raw/문서요약 텍스트" <서버>:immersive-TTS/data/raw/
  # 서버 → 맥북: 학습한 모델 가져오기
  scp -r <서버>:immersive-TTS/models/<실험명> models/
  ```
- 공개 다운로드가 되는 데이터(위키문헌 덤프 등)는 옮기지 말고 서버에서 `wget`으로 직접 받는다. 서버에는 curl도 없다.

### 두 곳에서 똑같이 돌아가는 코드

- 절대 경로를 코드에 박지 않는다. 레포 루트 기준 상대 경로나 CLI 인자로 받는다.
- 디바이스는 자동으로 고른다: `cuda` → `mps` → `cpu` 순.
- 의존성은 `environment.yml` 하나로 관리한다. 패키지를 추가하면 이 파일을 고치고, 두 컴퓨터 모두 `conda env update -f environment.yml --prune`을 실행한다.
- 한쪽에서만 필요한 패키지(예: CUDA 전용)가 생기면 바로 넣지 말고 사용자와 방법을 정한다.

## 환경

```bash
conda env create -f environment.yml   # 처음 한 번
conda activate immersive-tts
which python                           # 반드시 이 env의 python인지 확인
pytest
immersive-tts --help                   # 또는 python -m immersive_tts --help
```

- 맥북: pyenv가 같이 깔려 있어서 IDE 터미널에서 pyenv python이 먼저 잡힐 수 있다. 이때는 `conda deactivate`를 두 번 한 뒤 다시 `conda activate immersive-tts`.

## 서버 GPU 사용 규칙

서버는 연구실 공용이다.

반드시 singularity환경을 활성화 하여 작업을 해야 한다. 명령어는 다음과 같다.    

singularity shell --bind /data:/data --nv ~/torch20_cu118.sif

   source /opt/miniconda3/etc/profile.d/conda.sh


- 학습 전 `nvidia-smi`로 빈 GPU를 확인하고 `CUDA_VISIBLE_DEVICES`로 1장만 지정한다. 여러 장은 사용자에게 먼저 묻는다.
- 오래 걸리는 작업은 `tmux` 안에서 돌린다. SSH가 끊겨도 계속 돈다.
- 학습 결과는 `models/<실험명>/`에, 로그는 `logs/<실험명>.log`에 남긴다. 실험명은 `날짜_내용` 형식(예: `20261010_koelectra_baseline`).
- 실험 설정과 결과(정확도, F1, "필요" 재현율, 장르별 성능)는 `docs/실험기록.md`에 한 줄씩 추가한다. 이 파일은 git으로 공유한다.

## 레포 구조

```
src/immersive_tts/   패키지. cli.py가 명령 진입점(argparse 하위 명령)
tests/               pytest
docs/                시스템설계.md (설계 기준), 실험기록.md
data/raw/            원본 데이터 (git 제외)
data/processed/      가공 데이터 jsonl (git 제외)
models/              학습한 모델 (git 제외)
```

## 현재 진행 상황 (2026-10-09)

지금은 **문서 유형 분류기**를 만드는 중이다(설계 문서 1-2).

- 희곡 형식은 규칙으로 먼저 거른다. 분류기는 희곡이 아닌 텍스트에 대해 "LLM을 활용한 목소리 배정이 필요한가"를 이진 분류한다.
- 모델은 KoELECTRA-small. "필요" 재현율을 우선한다.
- 원본 데이터 (`data/raw/`, 맥북과 서버 모두 있음. 서버에는 논문·특허 중 논문 zip만 옮김):
  - `029.대규모 구매도서 기반 한국어 말뭉치 데이터/` 17GB. zip 번호가 KDC 코드. 810번대 문학(813 소설) → 필요, 그 외 → 불필요
  - `문서요약 텍스트/` 신문기사·사설 → 불필요. 법률은 제외
  - `018.논문자료 요약 데이터/` 논문 → 불필요. 특허는 제외
  - `wikisource/kowikisource-20261001-pages-articles.xml.bz2` 고전 소설 → 필요, 옛 문체 비문학 → 불필요
- 주의: 시대·문체로 라벨을 맞히는 지름길을 막아야 한다. 데이터는 `doc_id` 기준으로 직접 분할한다(AI Hub의 train/valid 분할은 쓰지 않음).
- 라벨링 규칙과 데이터 처리 방법은 설계 문서 1-3에 정리했다. 추론은 앞부분 512토큰만 쓴다.
- 다음 단계: 구매도서 unscramble 문장과 라벨링 JSON을 텍스트로 대조해 세부 KDC를 붙일 수 있는지 일부 데이터로 확인.
