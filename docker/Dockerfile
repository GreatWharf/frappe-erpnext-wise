# Build from the SAME pinned v16 image already used in your deployment.
# Your current image must contain Node/build tools needed by bench build.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
USER frappe
WORKDIR /home/frappe/frappe-bench
COPY --chown=frappe:frappe . apps/wise_bank_feed
RUN ./env/bin/pip install --no-cache-dir -e apps/wise_bank_feed \
    && (grep -qxF wise_bank_feed sites/apps.txt || printf '\nwise_bank_feed\n' >> sites/apps.txt) \
    && bench build --app wise_bank_feed
