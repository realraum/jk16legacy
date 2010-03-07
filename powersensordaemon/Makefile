##
##  powersensordaemon
##
##  Copyright (C) 2009 Christian Pointner <equinox@spreadspace.org>
##
##  This file is part of powersensordaemon.
##
##  powersensordaemon is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  any later version.
##
##  powersensordaemon is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with powersensordaemon. If not, see <http://www.gnu.org/licenses/>.
##

ifneq ($(MAKECMDGOALS),distclean)
include include.mk
endif

EXECUTABLE := powersensordaemon

OBJ := log.o \
       sig_handler.o \
       options.o \
       string_list.o \
       key_value_storage.o \
       command_queue.o \
       client_list.o \
       autosample.o \
       powersensordaemon.o


SRC := $(OBJ:%.o=%.c)

.PHONY: clean distclean

all: $(EXECUTABLE)

%.d: %.c
	@set -e; rm -f $@;                                 	 \
  $(CC) -MM $(CFLAGS) $< > $@.$$$$;                  	 \
  sed 's,\($*\)\.o[ :]*,\1.o $@ : ,g' < $@.$$$$ > $@;	 \
  rm -f $@.$$$$; echo '(re)building $@'

ifneq ($(MAKECMDGOALS),distclean)
-include $(SRC:%.c=%.d)
endif

powersensordaemon: $(OBJ)
	$(CC) $(OBJ) -o $@ $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c $<


distclean: clean
	find . -name *.o -exec rm -f {} \;
	find . -name "*.\~*" -exec rm -rf {} \;
	rm -f include.mk

clean:
	rm -f *.o
	rm -f *.d
	rm -f *.d.*
	rm -f $(EXECUTABLE)

