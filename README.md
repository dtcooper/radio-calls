# Radio Show Callboard + Amazon Mechanical Turk HIT

This is code that runs the VoIP callboard (which is really a SIP phone) for my
two radio shows _[This Is Going Well, I Think with David Cooper](https://jew.pizza)_
and _[//POOLABS//](https://kpiss.fm/show/poolabs/)_

As well, it includes the code I use to both submit and power the
[Amazon Mechanical Turk](https://www.mturk.com/)
[Human Intelligence Task](https://www.mturk.com/worker/help#what_is_hit) (HIT),
which in short is a work order that solicits calls from around the world.
Workers can then call into my shows using only their web browser.

## Technologies

Callboard

* Backend: [Flask](https://flask.palletsprojects.com/en/1.1.x/) and
  [Twilio](https://www.twilio.com/)'s Programmable Voice
  [SIP Registration](https://www.twilio.com/blog/support-regional-sip-registration)
  product.
* Taking Calls/VoIP: Any
  [SIP](https://en.wikipedia.org/wiki/Session_Initiation_Protocol) client, but
  I like [Blink](http://icanblink.com/) or [Zoiper](https://www.zoiper.com/)
  which support multiparty conferencing.

Amazon Mechanical Turk HIT

* Backend: Flask and Twilio, and [ipstack](https://ipstack.com/) for IP-based
  geolocation.
* Frontend: [alpine.js](https://github.com/alpinejs/alpine) as a JS framework,
  [chota](https://jenil.github.io/chota/) for CSS, and Twilio's
  [Client JS SDK](https://www.twilio.com/docs/voice/client/javascript) to place
  calls.
* HIT Management: [MTurk Manage](https://github.com/jtjacques/mturk-manage/)


## Running the Code

Honestly, don't bother. It's so specific to my setup, it's hard to imagine it
would be useful to anyone.

However, if you'd like to run it from your machine, install
[Docker](https://www.docker.com/) and do your best to figure out how to set
the variables in the file `.env.default`, copying it to `.env`. Then just
run `make` to build and run the container. The Flask server listens on port
`5142`.
