var SAVE_LOG_INTERVAL_MS = 180000
var LOG_INTERVAL_MS = 500

var data=[];
var t_fps='60';
var t_resolution='1920X1080';
var t_bitrate='40000';
var t_bufferLevel='10';
var saveBtn=document.getElementById("save_btn");
var loadBtn = document.getElementById("urlConfirmButton");

var absPlaybackStartTime = null;

function saveData(filename, text){
    var pom = document.createElement('a');
    pom.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    pom.setAttribute('download', filename);
    if (document.createEvent) {
        var event = document.createEvent('MouseEvents');
        event.initEvent('click', true, true);
        pom.dispatchEvent(event);
    } else {
        pom.click();
    }
}

function getTimeElapsedSec(startTime, endTime) {
    var curTime = new Date();
    // Date.getTime converts the datetime to a number of milliseconds since the epoch. Divide by 1000 to convert to seconds.
    var absTimeElapsedSec = (endTime.getTime() - startTime.getTime()) / 1000;
    return absTimeElapsedSec;
}

function onStalled() {
    stallStartTime = new Date();
};

function onStarted() {
    if (stallStartTime == null) {
        return; } // No stall was started. This might be the first time the stream started. Just ignore.

    var stallStopTime = new Date();

    var timeElapsedMs = getTimeElapsedSec(stallStartTime, stallStopTime) * 1000;

    // Log the time that the stall started.
    var logMsg = "STALL  " + timeElapsedMs + " ms";
    data.push(logMsg);

    stallStartTime = null;
};

function onQualityChanged(dashPlayer) {
    var dashAdapter = dashPlayer.getDashAdapter();
    var streamInfo = dashPlayer.getActiveStream().getStreamInfo();
    const periodIdx = streamInfo.index;
    var dashMetrics = dashPlayer.getDashMetrics();
    var repSwitch = dashMetrics.getCurrentRepresentationSwitch('video', true);
    var adaptation = dashAdapter.getAdaptationForType(periodIdx, 'video', streamInfo);
    var currentRep = adaptation.Representation_asArray.find(function (rep) {
        return rep.id === repSwitch.to
    });
    var resolution = currentRep.width + 'x' + currentRep.height;
    
    var nowTime = new Date();
    var timeElapsedSec;
    if (absPlaybackStartTime == null) {
        // Playback didn't start yet!
        timeElapsedSec = 0;
    } else {
        timeElapsedSec = getTimeElapsedSec(absPlaybackStartTime, nowTime);
    }

    var logMsg = "QUAL  at " + timeElapsedSec + " to " + resolution;
    data.push(logMsg);
};

saveBtn.onclick=function(){
	var t_data=data.join('\n')
    var dataString=t_data.toString();
    saveData("Tester_",dataString);
    // saveBtn.style.display="none";
    //startBtn.style.display="block";
}

loadBtn.onclick = function() {
    display();
}

/*var timer=setInterval(function(){
	//saveBtn.click();

    var doneLabel = document.getElementById("streamDoneLabel");
    doneLabel.style.display = "block";
}, SAVE_LOG_INTERVAL_MS)*/

function getManifestUrl() {
    var urlInput = document.getElementById("urlInput");
    if (!urlInput) {
        // The URL input field doesn't exist. Panic.
        console.log("Could not load URL from urlInput text input field. Loading default.");
        throw new Error("Could not find urlInput field to load the URL from!");
        //return "http://192.168.8.14/manifest_20000ms.mpd?t="+datetime; // Home Dell server
        //return "http://130.215.30.14/manifest.mpd?t="+datetime; // Xiaokun's server
        //return "http://mlcneta.cs.wpi.edu/manifest_20000ms.mpd?t="+datetime; // MLCNetA server
        //return "http://localhost/manifest_20000ms.mpd?t="+datetime; // localhost server
    }
    var url = new URL(urlInput.value);
    var datetime = new Date();
    url.searchParams.set("t", datetime)
    return url.toString();
}

<!--setup the video element and attach it to the Dash player-->
function display(){
    var datetime = new Date();
    console.log(datetime)
    var url = getManifestUrl();
    //var url = "http://192.168.8.14/manifest_20000ms.mpd?t="+datetime; // Home Dell server
    //var url = "http://130.215.30.14/manifest.mpd?t="+datetime; // Xiaokun's server
    //var url = "http://mlcneta.cs.wpi.edu/manifest_20000ms.mpd?t="+datetime; // MLCNetA server
    //var url = "http://localhost/manifest_20000ms.mpd?t="+datetime; // localhost server
    var player = dashjs.MediaPlayer().create();
    player.updateSettings({
        streaming: {
        buffer:{
            bufferToKeep: 20, // Default
            stableBufferTime: 20, // Default: 12
            bufferTimeAtTopQuality: 40, // Default: 30
            fastSwitchEnabled: true, //  Default
            initialBufferLevel: NaN // Default
        }
        }
    });
    
    player.initialize(document.querySelector("#video"), url, true);
    player.on(dashjs.MediaPlayer.events["PLAYBACK_STARTED"], function () {
        // Store a variable of when the playback started, as long as one hasn't been started before.
        // NOTE: This will not factor in if the user paused and then played the stream again. Considering they could seek around to other parts of the video, I'm ignoring the complexities of this and am just starting the timer once at the beginning.
        if (absPlaybackStartTime == null) {
            absPlaybackStartTime = new Date();
        }
    });
    player.on(dashjs.MediaPlayer.events["PLAYBACK_ENDED"], function () {
        clearInterval(eventPoller);
        clearInterval(bitrateCalculator);
        //clearInterval(timer);
        // Log the last set of data.
        recordStreamMetrics(player);
        // Now save the metric data to disk.
        saveBtn.click();
        var doneLabel = document.getElementById("streamDoneLabel");
        doneLabel.style.display = "block";
    });
    player.on(dashjs.MediaPlayer.events["BUFFER_EMPTY"], onStalled);
    player.on(dashjs.MediaPlayer.events["BUFFER_LOADED"], onStarted);
    player.on(dashjs.MediaPlayer.events["QUALITY_CHANGE_REQUESTED"], function() {
        onQualityChanged(player)
    });

    var eventPoller = setInterval(() => recordStreamMetrics(player), LOG_INTERVAL_MS);

    if (video.webkitVideoDecodedByteCount !== undefined) {
        var lastDecodedByteCount = 0;
        const bitrateInterval = 5;
        var bitrateCalculator = setInterval(function () {
            var calculatedBitrate = (((video.webkitVideoDecodedByteCount - lastDecodedByteCount) / 1000) * 8) / bitrateInterval;
            document.getElementById('calculatedBitrate').innerText = Math.round(calculatedBitrate) + " Kbps";
            lastDecodedByteCount = video.webkitVideoDecodedByteCount;
        }, bitrateInterval * 1000);
    } else {
        document.getElementById('chrome-only').style.display = "none";
    }

};

function recordStreamMetrics(player) {
    var streamInfo = player.getActiveStream().getStreamInfo();
    var dashMetrics = player.getDashMetrics();
    var dashAdapter = player.getDashAdapter();

    if (dashMetrics && streamInfo) {
        const periodIdx = streamInfo.index;
        var repSwitch = dashMetrics.getCurrentRepresentationSwitch('video', true);
        var bufferLevel = dashMetrics.getCurrentBufferLevel('video', true);
        var bitrate = repSwitch ? Math.round(dashAdapter.getBandwidthForRepresentation(repSwitch.to, periodIdx) / 1000) : NaN;
        var adaptation = dashAdapter.getAdaptationForType(periodIdx, 'video', streamInfo);
        var currentRep = adaptation.Representation_asArray.find(function (rep) {
            return rep.id === repSwitch.to
        })
        var frameRate = currentRep.frameRate;
        var resolution = currentRep.width + 'x' + currentRep.height;
        var cur_biterate = player.getAverageThroughput('video', true);

        var t_time=document.getElementById('video').currentTime;

        t_fps=frameRate;
        t_resolution=resolution;
        t_bitrate=bitrate;
        t_bufferLevel=bufferLevel;

        var nowTime = new Date();
        // Date.getTime() returns milliseconds, so divide by 1000 to convert to seconds.
        var absTimeElapsedSec = getTimeElapsedSec(absPlaybackStartTime, nowTime);

        temp_data="LOG  "+absTimeElapsedSec+","+t_time+':'+t_fps+','+t_resolution+','+t_bitrate+','+t_bufferLevel;
        data.push(temp_data);


        document.getElementById('bufferLevel').innerText = bufferLevel + " secs";
        document.getElementById('framerate').innerText = frameRate + " fps";
        document.getElementById('reportedBitrate').innerText = bitrate + " Kbps";
        document.getElementById('resolution').innerText = resolution;
        // document.getElementById('calculatedBitrate').innerText = Math.round(cur_biterate);
    }
};