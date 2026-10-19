# The hosted Builder pilot (Railway): the Builder app plus the Python server in hosted,
# read-only mode. Testers' drafts live in Supabase; the server never writes the repo files.
# Env (Railway variables): SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY,
# JZP_FEEDBACK_URL, optional JZP_BASE_FONT_OBJECT (default assets/TW-Kai-98.ttf). Railway sets PORT.
# Local try: docker build -t jzp-builder . && docker run --rm -p 5713:5713 --env-file .env jzp-builder

FROM node:22-slim AS app
WORKDIR /repo/app
COPY app/package.json app/package-lock.json ./
RUN npm ci
COPY app/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 JZP_HOSTED=1
WORKDIR /repo/src-fonttools
COPY src-fonttools/pyproject.toml ./
RUN pip install --no-cache-dir "fonttools>=4.50" "picosvg>=0.20" "skia-pathops>=0.9" "uharfbuzz>=0.39"
COPY src-fonttools/jzpbuild ./jzpbuild
COPY src-fonttools/inputs ./inputs
COPY --from=app /repo/app/build /repo/app/build
RUN useradd --create-home builder && mkdir -p src_font && chown -R builder /repo/src-fonttools
USER builder
# the base font (TW-Kai) is fetched from Supabase Storage at startup, then main's font is built once
CMD ["python3", "-m", "jzpbuild.webserver", "--hosted", "--host", "0.0.0.0"]
