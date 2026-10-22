#!/usr/bin/env bash
# One-time setup of the Builder's backup on Google Cloud Run (docs/maintainers/setup.md
# "Google Cloud Run"). Safe to run again: what exists is left alone, the Supabase settings are
# updated. Needs gcloud signed in as the project's owner:
#
#   PROJECT=<project id> REGION=us-central1 bash deploy/cloudrun-setup.sh
#
# Makes: the Artifact Registry repository `jzp` (with a clean-up policy), the service accounts
# jzp-deploy (GitHub Actions) and jzp-run (the services), Workload Identity Federation for this
# repository only, the services jzp-builder and jzp-builder-staging (a placeholder image until the
# first deploy) with their Supabase settings, the service keys in Secret Manager. Prints the
# repository variables for GitHub at the end.
set -euo pipefail

: "${PROJECT:?set PROJECT to the Google Cloud project id}"
REGION=${REGION:-us-central1}
GITHUB_REPO=${GITHUB_REPO:-neuralfirings/JianZiPu}
DEPLOY_SA="jzp-deploy@$PROJECT.iam.gserviceaccount.com"
RUN_SA="jzp-run@$PROJECT.iam.gserviceaccount.com"
g() { gcloud --project="$PROJECT" --quiet "$@"; }

exists() { "$@" >/dev/null 2>&1; }

echo "== APIs"
g services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com
NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')

echo "== Artifact Registry"
exists g artifacts repositories describe jzp --location="$REGION" ||
  g artifacts repositories create jzp --repository-format=docker --location="$REGION" \
    --description="JZP Font Builder images (.github/workflows/cloudrun.yml)"
# keep production's image (tag main) and the 10 newest; delete the rest after 30 days
policy=$(mktemp)
cat > "$policy" <<'JSON'
[
  {"name": "keep-production", "action": {"type": "Keep"}, "condition": {"tagState": "tagged", "tagPrefixes": ["main"]}},
  {"name": "keep-newest", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 10}},
  {"name": "delete-old", "action": {"type": "Delete"}, "condition": {"tagState": "any", "olderThan": "30d"}}
]
JSON
g artifacts repositories set-cleanup-policies jzp --location="$REGION" --policy="$policy" --no-dry-run
rm -f "$policy"

echo "== Service accounts"
exists g iam service-accounts describe "$DEPLOY_SA" ||
  g iam service-accounts create jzp-deploy --display-name="JZP Builder deploys (GitHub Actions)"
exists g iam service-accounts describe "$RUN_SA" ||
  g iam service-accounts create jzp-run --display-name="JZP Builder on Cloud Run"
g projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$DEPLOY_SA" \
  --role=roles/run.developer --condition=None >/dev/null
g artifacts repositories add-iam-policy-binding jzp --location="$REGION" \
  --member="serviceAccount:$DEPLOY_SA" --role=roles/artifactregistry.writer >/dev/null
g iam service-accounts add-iam-policy-binding "$RUN_SA" \
  --member="serviceAccount:$DEPLOY_SA" --role=roles/iam.serviceAccountUser >/dev/null

echo "== Workload Identity Federation (GitHub Actions of $GITHUB_REPO only)"
exists g iam workload-identity-pools describe github --location=global ||
  g iam workload-identity-pools create github --location=global --display-name="GitHub Actions"
exists g iam workload-identity-pools providers describe github --location=global --workload-identity-pool=github ||
  g iam workload-identity-pools providers create-oidc github --location=global --workload-identity-pool=github \
    --display-name="GitHub" --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository == '$GITHUB_REPO'"
g iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$NUMBER/locations/global/workloadIdentityPools/github/attribute.repository/$GITHUB_REPO" >/dev/null

# service <name> <secret> <label>: asks for that service's Supabase settings, stores the service
# key, and creates the service (placeholder image) or updates its settings
service() {
  local name=$1 secret=$2 label=$3 url anon key
  echo "== $name ($label)"
  read -r -p "  SUPABASE_URL for $label (https://<project>.supabase.co): " url
  read -r -p "  SUPABASE_ANON_KEY for $label: " anon
  read -r -s -p "  SUPABASE_SERVICE_KEY for $label (hidden; Enter keeps the stored one): " key; echo
  if ! exists g secrets describe "$secret"; then
    [ -n "$key" ] || { echo "  a new secret needs the service key"; exit 1; }
    printf %s "$key" | g secrets create "$secret" --replication-policy=automatic --data-file=- >/dev/null
  elif [ -n "$key" ]; then
    printf %s "$key" | g secrets versions add "$secret" --data-file=- >/dev/null
  fi
  g secrets add-iam-policy-binding "$secret" --member="serviceAccount:$RUN_SA" \
    --role=roles/secretmanager.secretAccessor >/dev/null
  local settings=(--update-env-vars="SUPABASE_URL=$url,SUPABASE_ANON_KEY=$anon"
                  --update-secrets="SUPABASE_SERVICE_KEY=$secret:latest")
  if exists g run services describe "$name" --region="$REGION"; then
    g run services update "$name" --region="$REGION" "${settings[@]}"
  else
    g run deploy "$name" --region="$REGION" --image=us-docker.pkg.dev/cloudrun/container/hello \
      --service-account="$RUN_SA" --max-instances=1 "${settings[@]}"
  fi
  g run services add-iam-policy-binding "$name" --region="$REGION" \
    --member=allUsers --role=roles/run.invoker >/dev/null
}

service jzp-builder jzp-supabase-service-key "production"
service jzp-builder-staging jzp-staging-supabase-service-key "staging (pull request previews)"

cat <<OUT

Done. In GitHub: Settings -> Secrets and variables -> Actions -> Variables, add:
  GCP_PROJECT_ID    $PROJECT
  GCP_REGION        $REGION
  GCP_WIF_PROVIDER  projects/$NUMBER/locations/global/workloadIdentityPools/github/providers/github
  GCP_DEPLOY_SA     $DEPLOY_SA
Then Actions -> cloudrun -> Run workflow (on main) for the first production deploy.
Production: $(gcloud run services describe jzp-builder --project="$PROJECT" --region="$REGION" --format='value(status.url)')
OUT
