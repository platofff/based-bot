FROM opensuse/leap:15.3
ADD ./requirements.txt /home/app/requirements.txt
RUN zypper ar -f https://download.opensuse.org/repositories/home:/flacco:/rtk:/php7/15.3/ imagemagick &&\
 zypper ar -f https://download.opensuse.org/repositories/Publishing:/TeXLive/openSUSE_Leap_15.3/ texlive &&\
 zypper -n --gpg-auto-import-keys ref &&\
 ln -s /usr/share/zoneinfo/Europe/Moscow /etc/localtime &&\
 zypper -n in --no-recommends ImageMagick\
 noto-coloremoji-fonts\
 dejavu-fonts\
 curl\
 gcc-c++\
 tar\
 bzip2\
 timezone \
 texlive-oswald-fonts &&\
 ln -s /usr/lib64/gcc/x86_64-suse-linux/7/cc1plus /usr/bin/cc1plus &&\
 bash -c 'curl https://downloads.python.org/pypy/pypy3.7-v7.3.7-linux64.tar.bz2 | tee >(tar xjf - -C /tmp) | [ "$(shasum -a 256 -)" = "8332f923755441fedfe4767a84601c94f4d6f8475384406cb5f259ad8d0b2002  -" ]' || exit -1 &&\
 mv /tmp/pypy3.7-v7.3.7-linux64 /opt/pypy &&\
 /opt/pypy/bin/pypy3 -m ensurepip &&\
 /opt/pypy/bin/pypy3 -m pip install -U pip wheel &&\
 groupadd -g 2000 app &&\
 useradd -u 2000 -m app -g app &&\
 chown -R app:app /home/app &&\
 su app -c '/opt/pypy/bin/pypy3 -m pip install --user --no-warn-script-location -r /home/app/requirements.txt' &&\
 zypper -n rm --clean-deps curl tar gcc-c++ bzip2 &&\
 zypper -n clean
USER app
ADD . /home/app
WORKDIR /home/app
ENTRYPOINT ["/opt/pypy/bin/pypy3", "/home/app/main.py"]
