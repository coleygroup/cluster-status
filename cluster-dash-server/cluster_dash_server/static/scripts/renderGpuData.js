/**
 * Created by john on 30/03/2017.
 */

var nameLength = 30;

(function(){
    TESTER = document.getElementById('chart-div');

    function httpGetAsync(theUrl, callback)
    {
        var xmlHttp = new XMLHttpRequest();
        xmlHttp.onreadystatechange = function() {
            if (xmlHttp.readyState == 4 && xmlHttp.status == 200)
                callback(xmlHttp.responseText);
        };
        xmlHttp.open("GET", theUrl, true); // true for asynchronous
        xmlHttp.send(null);
    };


    var parseJsonBasics = function (jsonIn) {
        var machines = _.keys(jsonIn);
        var users = _.flatten(_.map(jsonIn, function (val) {
            return _.map(val, function (val) {
                // collect just the user ids from the gpus
                return _.keys(val["users"])
            })
        }));

        var uniqueUsers = _.uniq(users);


        return [uniqueUsers,machines]
    };



    let totalMemCreator = function (jsonIn) {
        // This function goes through the json and extracts

        let results = _.values(_.mapObject(jsonIn, function(val, key1) {
                                    return _.values(_.mapObject(val, function(val, key2) {
                                        let name = key1.concat("-",key2);
                                        let freeMem = val["total_mem"] - val["used_mem"];
                                        let totalMem = val["total_mem"];
                                        let last_poll = `${name}, Received: ${val["time_received_mins"]} mins ago... `;
                                        name = name.slice(0, nameLength)
                                        return [name, freeMem, totalMem, last_poll, val["time_received_mins"]]
                                    }));
        }));

        let flatResults = _.flatten(results, true);

        flatResults = _.filter(flatResults, function(arr) { return arr[2] > 3000;});
        flatResults = _.sortBy(flatResults, function(arr) {return arr[0]}).reverse();


        let staleTime = 10.;
        let flatResultsStale = _.filter(flatResults, function(arr) {return arr[4] > staleTime;});
        let flatResultsNew = _.filter(flatResults, function(arr) {return arr[4] < staleTime;});


        var resAll = [];
        for (let flatRes of [['rgb(6, 53, 130)', flatResultsNew], ['rgb(37,93,190)', flatResultsStale]]) {
            let [x, y, total_mem, last_poll, old_time] = _.zip.apply(this, flatRes[1]);
            // nb x and y switched as moved to a *horizontal* bar chart.
            let res =  {
                y:x,
                x:y,
                text:last_poll,
                name:"free memory",
                type: 'bar',
                orientation: 'h',
                marker: {
                    color: flatRes[0]
                }
            };
            resAll.push(res);

        }

        var gpuNames = _.map(flatResults, (arr) => arr[0]);
        console.log("free memory ", resAll);

        return [resAll, gpuNames]
    };

    var createUserPlot = function(jsonIn, user) {

        var results = [];
        for (let machineName in jsonIn) {
            if (jsonIn.hasOwnProperty(machineName)) {
                for (let gpuName in jsonIn[machineName]) {
                    if (jsonIn[machineName].hasOwnProperty(gpuName)) {
                        let machienGpuName = machineName.concat("-", gpuName);

                        let [totalMem, text] = goThroughUsersDict(jsonIn[machineName][gpuName]["users"][user], user);
                        machienGpuName =  machienGpuName.slice(0, nameLength)
                        results.push([machienGpuName, totalMem, text]);



                    };
                };

            };
        };

        // var results = [];
        // for (let gpuName of orderedMachineGPUNames) {
        //     results.push(resultsPreSort[gpuName])
        // }

        let [x, y, text] = _.zip.apply(null, results);

        // nb x and y switched as moved to a *horizontal* bar chart.
        let userData = {
            y:x,
            x:y,
            text:text,
            name:user,
            type: 'bar',
            orientation: 'h',
        };

        return userData;
    };


    var goThroughUsersDict = function(usersDict, user) {

        let totalMem = 0;
        let text = `${user}:`;

        for (let process in usersDict) {
            if (usersDict.hasOwnProperty(process)) {
                let mem = usersDict[process]["mem"];
                let time = usersDict[process]["time"];
                totalMem += mem;

                text += `${process}(mem: ${mem}, time: ${time}), `

            };
        };

        return [totalMem, text]
    };

    var plotter = function plotter(jsonIn) {
        jsonIn = JSON.parse(jsonIn);

        let [users, machines] = parseJsonBasics(jsonIn);

        let [total, gpuNames] = totalMemCreator(jsonIn);


        let userData = _.map(users, val => createUserPlot(jsonIn, val));

        var data = total.concat(userData);

        var layout = {
            barmode: 'stack',
            margin: {"l": 200  },
            font: {"size": 10},
            hovermode: 'closest'
        };


        Plotly.newPlot('chart-div', data, layout);
    };




    httpGetAsync("/data-out/gpu-data-simple", plotter)
})();

