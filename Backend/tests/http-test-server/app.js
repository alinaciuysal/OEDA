var express = require('express');
var bodyParser = require('body-parser');
var app = express();
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({extended: true}));

/**
 * Optimizing function:
 *
 *  Test Range: x:[-4.0-6.0] y:[-10,10]
 *
 *  f(x,y) = 0.4+-1*(0.3*(1-x)*x+y*(2-y)*0.3+x*y/100)
 *
 *  Global minimum at (0.51681, 1.00861) with 0.0198944
 *
 *  Additional random variance can be enabled
 *
 *  TODO: integrate more functions and allow selection.
 *  see: https://en.wikipedia.org/wiki/Test_functions_for_optimization
 */

/** the main config variable */
var x = 0.0;
var y = 0.0;

var enableRandom = true;

app.get('/', function (req, res) {
    var rnd = 1;
    if (enableRandom) {
        rnd = Math.random()
    }
    res.send(JSON.stringify({
        x: x,
        y: y,
        result: rnd * ( 0.4 + -1 * (0.3 * (1 - x) * x + y * (2 - y) * 0.3 + x * y / 100))
    }));
});

app.post('/', function (req, res) {
    if (req.body) {
        console.log("Got value changes: x:" + req.body.x + " - y:" + req.body.y);
        x = req.body.x || x;
        y = req.body.y || y
    }
    res.send("ok");
});

app.listen(3003, function () {
    console.log('OEDA HTTP test app listening on port 3003!');
});
