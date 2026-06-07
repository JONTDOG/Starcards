# StarCards

StarCards turns bookmark-structured PDFs into Anki-ready study cards.

This workspace is being refactored into three layers:

1. Shared backend core
2. Verification and grounding pipeline
3. GUI front ends later

## Current direction

- Keep the core reusable by both desktop and browser apps.
- Add source-grounded verification to reduce hallucinated answers.
- Preserve one canonical output model for all card types.

## Useful commands

- Inspect PDF sections:
  - `python scripts/inspect_pdf.py path\to\book.pdf`
- Generate cards:
  - `python scripts/generate_pdf_cards.py path\to\book.pdf path\to\output`
- Audit output files:
  - `python scripts/audit_outputs.py path\to\output`
- Verify a single output file against source text:
  - `python scripts/verify_output.py path\to\cards.txt path\to\source.txt`
- Launch the Streamlit app:
  - `streamlit run app/streamlit_app.py`

## Anki flow

- Generate cards in the app.
- Download the `.apkg` package from the app.
- Import the `.apkg` manually into Anki.
- No Python is needed on the teacher or student machine.

## Deployment

The commands below assume a fresh Ubuntu 24.04 DigitalOcean droplet and a repository clone URL you control.

Before you start:
- Create an `A` record for your domain and, optionally, `www` so both point to the droplet public IP.
- Wait for DNS propagation to finish. You can verify it with `dig +short YOUR_DOMAIN_HERE`.

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin certbot
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
newgrp docker

sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

git clone https://github.com/YOUR_ORG/StarCards.git
cd StarCards
mkdir -p runs

# Replace the placeholder domain in nginx.conf with your real domain.
perl -0pi -e 's/starcards\.example\.com/YOUR_DOMAIN_HERE/g' nginx.conf

# Get the certificate before starting nginx. This uses port 80 temporarily.
sudo certbot certonly --standalone \
  -d YOUR_DOMAIN_HERE \
  -d www.YOUR_DOMAIN_HERE \
  --agree-tos \
  --email jonmt2020@gmail.com \
  --non-interactive

docker compose up -d --build
docker compose logs --tail=50 starcards nginx
```

For later updates, run:

```bash
chmod +x deploy.sh
./deploy.sh
```

That script assumes your Let's Encrypt certificate already exists from the first-time issuance step above.

The app is exposed on port `443` through nginx and persists generated APKG files in `./runs`.

For automatic renewal, add a root cron entry:

```bash
sudo crontab -e
```

Add this line, replacing the repo path if needed:

```bash
0 3 * * * cd /home/YOUR_USER/StarCards && docker compose stop nginx && /usr/bin/certbot renew --quiet && docker compose up -d nginx
```
