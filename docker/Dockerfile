FROM condaforge/miniforge3

WORKDIR /app/
COPY . /app/

RUN bash conda_env.sh
CMD ["bash", "run.sh"]