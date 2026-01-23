# ---------- build stage ----------
FROM public.ecr.aws/lambda/python:3.14 AS builder

# Install git only in the build stage
RUN dnf install -y git && dnf clean all

COPY requirements.txt .

RUN pip install \
    -r requirements.txt \
    --target /opt/python

RUN pip install \
  git+https://github.com/BonJamon/TheNewsAPI_MCP.git \
  --target /opt/python


# ---------- runtime stage ----------
FROM public.ecr.aws/lambda/python:3.14

# Copy dependencies from builder
COPY --from=builder /opt/python ${LAMBDA_TASK_ROOT}

# Copy your application code
COPY api ${LAMBDA_TASK_ROOT}/api
COPY factchecker ${LAMBDA_TASK_ROOT}/factchecker
COPY lambda_handler.py ${LAMBDA_TASK_ROOT}

ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"

CMD ["lambda_handler.handler"]

ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"
