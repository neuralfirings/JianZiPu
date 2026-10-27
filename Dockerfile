# The hosted Builder pilot (Railway): the Builder app plus the Python server in hosted,
# read-only mode. Testers' drafts live in Supabase; the server never writes the repo files.
# Env (Railway variables): SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY,
# JZP_FEEDBACK_URL, optional JZP_BASE_FONT_OBJECT (default assets/TW-Kai-98.ttf). Railway sets PORT.
# Local try: docker build -t jzp-builder . && docker run --rm -p 5713:5713 --env-file .env jzp-builder

FROM node:26-slim AS app
WORKDIR /repo/app
COPY app/package.json app/package-lock.json ./
RUN npm ci
COPY app/ ./
RUN npm run build

FROM python:3.15-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 JZP_HOSTED=1
WORKDIR /repo/builder
COPY builder/pyproject.toml builder/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY builder/VERSION ./
COPY CHANGELOG.md /repo/CHANGELOG.md
COPY builder/jzpbuild ./jzpbuild
COPY builder/inputs ./inputs
COPY --from=app /repo/app/build /repo/app/build
RUN useradd --create-home builder && mkdir -p src_font && chown -R builder /repo/builder
USER builder
# the base font (TW-Kai) is fetched from Supabase Storage at startup, then main's font is built once
CMD ["python3", "-m", "jzpbuild.webserver", "--hosted", "--host", "0.0.0.0"]
