var SAVE_LOG_INTERVAL_MS = 180000
var LOG_INTERVAL_MS = 500

// Meant to match the scheme portion of a URL (eg "https://"). Based on comments in https://stackoverflow.com/a/8206299.
// Using a regex for a situation with as much variation as this is horrible but I couldn't find a simple alternative.
var URL_SCHEME_REGEX = /^\/\/|^.*?:(?:\/\/)?/;
// Matches all the content of the query parameters in the URL plus the ? at the start.
var URL_QUERY_PARAMS_REGEX = /\?(?:.)*$/;

var data=[];
var t_fps='60';
var t_resolution='1920X1080';
var t_bitrate='40000';
var t_bufferLevel='10';
var saveBtn=document.getElementById("save_btn");
var loadBtn = document.getElementById("urlConfirmButton");

var absVideoLoadStartTime = null;
var absPlaybackStartTime = null;
var videoUrl = null;
var outputFileName = null;

function saveData(encodedFileName, text){
    console.log("Saving data to " + encodedFileName);
    var pom = document.createElement('a');
    pom.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    pom.setAttribute('download', encodedFileName);
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
    let absTimeElapsedSincePlayBackStartSec = getTimeElapsedSec(absPlaybackStartTime, stallStartTime)

    let logMsg = "STALL  started at " + absTimeElapsedSincePlayBackStartSec +" sec";
    data.push(logMsg);
};

function onStarted() {
    if (stallStartTime == null) {
        return; } // No stall was started. This might be the first time the stream started. Just ignore.

    var stallStopTime = new Date();

    var timeElapsedMs = getTimeElapsedSec(stallStartTime, stallStopTime) * 1000;
    let absTimeElapsedSincePlayBackStartSec = getTimeElapsedSec(absPlaybackStartTime, stallStopTime)

    // Log the time that the stall started.
    var logMsg = "STALL  " + timeElapsedMs + " ms and stopped at "+ absTimeElapsedSincePlayBackStartSec+" sec";
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
    // Removes the scheme identifier (eg "https://") from the front of the URL so the result is file-system compatible.
    var videoUrlAfterProtocol = videoUrl.replace(URL_SCHEME_REGEX, "");
    // Removes the query parameters from the end of the URL so the whole timestamp doesn't spam the file name.
    var videoUrlCleaned = encodeURIComponent(videoUrlAfterProtocol.replace(URL_QUERY_PARAMS_REGEX, ""));
    console.log("URL AFTER: " + videoUrlCleaned);
    outputFileName = "Tester_" + videoUrlCleaned + ".log";
    saveData(outputFileName, dataString);
    displayDoneLabel();
    // saveBtn.style.display="none";
    //startBtn.style.display="block";
}

loadBtn.onclick = function() {
    display();
}

function displayDoneLabel() {
    var doneLabel = document.getElementById("streamDoneLabel");
    if (outputFileName !== null && outputFileName.trim() !== "") {
        doneLabel.textContent = outputFileName;
    }
    doneLabel.style.display = "block";
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

function display(){
    var datetime = new Date();
    console.log(datetime)
    absVideoLoadStartTime = datetime;
    videoUrl = getManifestUrl();
    //videoUrl = "http://192.168.8.14/manifest_20000ms.mpd?t="+datetime; // Home Dell server
    //videoUrl = "http://130.215.30.14/manifest.mpd?t="+datetime; // Xiaokun's server
    //videoUrl = "http://mlcneta.cs.wpi.edu/manifest_20000ms.mpd?t="+datetime; // MLCNetA server
    //videoUrl = "http://localhost/manifest_20000ms.mpd?t="+datetime; // localhost server
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
    
    player.initialize(document.querySelector("#video"), videoUrl, true);
    player.on(dashjs.MediaPlayer.events["PLAYBACK_STARTED"], function () {
        // Store a variable of when the playback started, as long as one hasn't been started before.
        // NOTE: This will not factor in if the user paused and then played the stream again. Considering they could seek around to other parts of the video, I'm ignoring the complexities of this and am just starting the timer once at the beginning.
        if (absPlaybackStartTime == null) {
            absPlaybackStartTime = new Date();
            // Get the time between when the video first started to load and now, when it started playing.
            var timeElapsedSec = getTimeElapsedSec(absVideoLoadStartTime, absPlaybackStartTime);
            var logMsg = "START  took " + timeElapsedSec * 1000 + " ms";
            data.push(logMsg);
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
        var curThroughput = player.getAverageThroughput('video', true);

        var t_time=document.getElementById('video').currentTime;

        t_fps=frameRate;
        t_resolution=resolution;
        t_bitrate=bitrate;
        t_bufferLevel=bufferLevel;

        var nowTime = new Date();
        // Date.getTime() returns milliseconds, so divide by 1000 to convert to seconds.
        var absTimeElapsedSec = getTimeElapsedSec(absPlaybackStartTime, nowTime);

        temp_data="LOG  "+absTimeElapsedSec+","+t_time+':'+t_fps+','+t_resolution+','+t_bitrate+','+t_bufferLevel+','+curThroughput;
        data.push(temp_data);


        document.getElementById('bufferLevel').innerText = bufferLevel + " secs";
        document.getElementById('framerate').innerText = frameRate + " fps";
        document.getElementById('reportedBitrate').innerText = bitrate + " Kbps";
        document.getElementById('resolution').innerText = resolution;
        document.getElementById('curThroughput').innerText = Math.round(curThroughput);
    }
};