FROM git.softline.com/registry/python-image:v2
COPY hosts.py /hosts.py
ENTRYPOINT ["sh", "-c", "python /hosts.py && echo \"::set-output name=result::$(cat output.json)\""]