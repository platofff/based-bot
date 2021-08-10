FROM opensuse/leap:15.3
ADD . /home/app
RUN zypper ar -f https://download.opensuse.org/repositories/home:/flacco:/rtk:/php7/15.3/ imagemagick &&\
 zypper -n --gpg-auto-import-keys ref &&\
 zypper -n in --no-recommends ImageMagick\
 noto-coloremoji-fonts\
 dejavu-fonts\
 curl\
 gcc-c++ \
 tar \
 bzip2 &&\
 ln -s /usr/lib64/gcc/x86_64-suse-linux/7/cc1plus /usr/bin/cc1plus &&\
 sh -c 'curl https://downloads.python.org/pypy/pypy3.7-v7.3.5-linux64.tar.bz2 | tar xjf - -C /tmp' &&\
 mv /tmp/pypy3.7-v7.3.5-linux64/* /usr/local/ &&\
 pypy3 -m ensurepip &&\
 pypy3 -m pip install -U pip wheel &&\
 pypy3 -m pip install -r /home/app/requirements.txt &&\
 zypper -n rm --clean-deps curl tar gcc-c++ bzip2 &&\
 zypper -n clean &&\
 groupadd -g 2000 app &&\
 useradd -u 2000 -m app -g app
USER app
WORKDIR /home/app
ENTRYPOINT ["/home/app/main.py"]
