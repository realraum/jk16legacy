## realraum tuer daemon

all: mifare-read

mifare-read: mifare-read.c
	$(CC) $(CFLAGS) -o $@ $<

