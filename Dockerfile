FROM opensuse/leap:15.3
ADD . /home/app
RUN zypper ar -f https://download.opensuse.org/repositories/home:/flacco:/rtk:/php7/15.3/ imagemagick &&\
 zypper -n --gpg-auto-import-keys ref &&\
 ln -s /usr/share/zoneinfo/Europe/Moscow /etc/localtime &&\
 zypper -n in --no-recommends ImageMagick\
 noto-coloremoji-fonts\
 dejavu-fonts\
 curl\
 gcc-c++\
 tar\
 bzip2\
 timezone &&\
 ln -s /usr/lib64/gcc/x86_64-suse-linux/7/cc1plus /usr/bin/cc1plus &&\
 sh -c 'curl https://downloads.python.org/pypy/pypy3.7-v7.3.6-linux64.tar.bz2 | tar xjf - -C /tmp' &&\
 mv /tmp/pypy3.7-v7.3.5-linux64 /opt/pypy &&\
 /opt/pypy/bin/pypy3 -m ensurepip &&\
 /opt/pypy/bin/pypy3 -m pip install -U pip wheel &&\
 groupadd -g 2000 app &&\
 useradd -u 2000 -m app -g app &&\
 chown -R app:app /home/app &&\
 su app -c '/opt/pypy/bin/pypy3 -m pip install --user --no-warn-script-location -r /home/app/requirements.txt' &&\
 zypper -n rm --clean-deps curl tar gcc-c++ bzip2 &&\
 zypper -n clean
USER app
WORKDIR /home/app
ENTRYPOINT ["/opt/pypy/bin/pypy3", "/home/app/main.py"]
