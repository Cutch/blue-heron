sudo apt update  
sudo apt-get install -y cmake git  
git clone https://github.com/tensorflow/tensorflow.git tensorflow_src  
mkdir tflite_build  
cd tflite_build  


sudo apt-get install libc6 libncurses5 libreadline-dev libffi-dev libbz2-dev libssl-dev zlib1g-dev libzstd1 libsqlite3-dev liblzma5 liblzma-dev python3-dev build-essentials  

CI_BUILD_PYTHON=python3.9 PYTHON=python3.9 tensorflow/lite/tools/pip_package/build_pip_package_with_cmake.sh rpi  


SETUPTOOLS_USE_DISTUTILS=stdlib PYTHON_CONFIGURE_OPTS="--enable-shared --with-ensurepip=no" CFLAGS="-m32" LDFLAGS="-m32" pyenv install 3.9.2  
