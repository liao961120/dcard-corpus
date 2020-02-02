FROM nickgryg/alpine-pandas:3.7.6
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app
RUN pip install -r requirements.txt
RUN pip install gunicorn
COPY . /usr/src/app
EXPOSE 80
# Command to run when running docker run
CMD [ "gunicorn", "--timeout", "90",  "-b", "0.0.0.0:80", "main:app" ]
# docker build -t <tag-name> <path>
# docker build -t asbc .
# docker container run -it -p 127.0.0.1:1420:80 -v /home/liao/Desktop/ASBC/data/:/usr/src/app/data/ asbc

