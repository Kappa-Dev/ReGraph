FROM ylecornec/regraph_base
MAINTAINER Le Cornec Yves-Stan

COPY . ReGraph
RUN git clone https://github.com/Kappa-Dev/RegraphGui.git
RUN ln -s ../RegraphGui ReGraph/RegraphGui
EXPOSE 5000
WORKDIR ReGraph
CMD python3 webserver.py
