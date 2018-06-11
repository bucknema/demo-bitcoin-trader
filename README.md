# demo-bitcoin-trader
Cloud webapp with a REST API for demo trading bitcoin with the Coindesk BPI price
GET /
Gets the main site with sign-in button to retrieve user-specific OAuth token. 
(Get yourself two separate tokens with two separate Google accounts if you want to setup the Postman collection variables ‘user1’ and ‘user2’ for testing)

People
####
GET/people
Returns all the “people” associated with a user.

GET/people/{{personID}}
Shows details for single person by ID

POST/people
Creates a new person. 

Expected POST body fields: 
{“username”: “”, 
“email”: “”, 
“btc_value”: “”, 
“usd_value”: “”
}
Username is required.
People’s BTC and USD holding amount default to 0.0 unless provided in body at creation.

PUT/people/{{personID}}
Replace data of person by ID

DELETE/people/{{personID}}
Deletes a person and removes their username from any trade(s)

Trades
####
GET/trades
Returns all trades specific to a user

GET/trades/{{tradeID}}
Returns a specific trade for the user

POST/trades
Creates a new trade. Rate and timestamp default to Coindesk API values unless provided in POST body.

Expected POST body fields: 
{“username”: “User who made the trade”, 
“time_stamp”: “Time trade was made”, 
“rate”: “Floating-point BTC price in USD at time of trade”, 
“amount”: “Floating-point amount of BTC bought or sold”,
“buying”: “Boolean that is TRUE if buying BTC with USD; FALSE if selling BTC for USD”
}
Buying defaults to True if not specified by the user, and amount defaults to 0.0 

PUT/trades/{{tradeID}}
Replaces trade data. Will timestamp and rate default to live Coindesk data if data isn’t provided.

DELETE/trades/{{tradeID}}
Removes a trade.
