-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:52 PM
-- Cached decompilation

local v_u_1 = {
    ["AudioAssetId"] = "rbxassetid://8160534444",
    ["AudioFilename"] = "Monday Night Monsters (Tutorial)",
    ["AudioDescription"] = "Welcome to RoBeats! Want to learn how to play? We\'re here to show you!",
    ["AudioCoverImageAssetId"] = "rbxassetid://698514070",
    ["AudioArtist"] = "FinnMK",
    ["AudioDifficulty"] = 1,
    ["AudioTimeOffset"] = -75,
    ["AudioVolume"] = 0.5,
    ["AudioNotePrebufferTime"] = 1500,
    ["AudioMod"] = 2,
    ["AudioHitSFXGroup"] = 2,
    ["IsRemix"] = true,
    ["VIP"] = true,
    ["Priority"] = 1,
    ["BPM"] = 100,
    ["HitObjects"] = {},
    ["TimingPoints"] = {
        {
            ["Time"] = -30,
            ["BeatLength"] = 600
        }
    }
}
local function _(p2, p3) --[[ Name: note ]] --[[ Line: 18 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
        ["Time"] = p2,
        ["Type"] = 1,
        ["Track"] = p3
    }
end;
local function _(p4, p5, p6) --[[ Name: hold ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
        ["Time"] = p4,
        ["Type"] = 2,
        ["Track"] = p5,
        ["Duration"] = p6
    }
end;
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 2370,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 4170,
    ["Type"] = 1,
    ["Track"] = 2
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 4770,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 6570,
    ["Type"] = 1,
    ["Track"] = 3
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 7170,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 8370,
    ["Type"] = 2,
    ["Track"] = 2,
    ["Duration"] = 1200
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 10770,
    ["Type"] = 2,
    ["Track"] = 1,
    ["Duration"] = 1200
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 13170,
    ["Type"] = 2,
    ["Track"] = 3,
    ["Duration"] = 1200
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 15570,
    ["Type"] = 2,
    ["Track"] = 1,
    ["Duration"] = 1200
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 17370,
    ["Type"] = 1,
    ["Track"] = 2
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 17970,
    ["Type"] = 2,
    ["Track"] = 3,
    ["Duration"] = 1500
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 21870,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 22470,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 23070,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 23670,
    ["Type"] = 1,
    ["Track"] = 3
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 24270,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 24870,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 25470,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 26070,
    ["Type"] = 1,
    ["Track"] = 2
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 26670,
    ["Type"] = 1,
    ["Track"] = 3
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 27270,
    ["Type"] = 1,
    ["Track"] = 3
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 27870,
    ["Type"] = 2,
    ["Track"] = 4,
    ["Duration"] = 1200
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 29670,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 30270,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 30870,
    ["Type"] = 1,
    ["Track"] = 2
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 31470,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 32070,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 32670,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 33270,
    ["Type"] = 1,
    ["Track"] = 3
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 33870,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 34470,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 35070,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 35670,
    ["Type"] = 1,
    ["Track"] = 4
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 36270,
    ["Type"] = 1,
    ["Track"] = 2
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 36870,
    ["Type"] = 1,
    ["Track"] = 2
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 37470,
    ["Type"] = 1,
    ["Track"] = 2
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 38370,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 38370,
    ["Type"] = 1,
    ["Track"] = 4
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 38970,
    ["Type"] = 2,
    ["Track"] = 2,
    ["Duration"] = 1800
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 40770,
    ["Type"] = 2,
    ["Track"] = 3,
    ["Duration"] = 900
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 42270,
    ["Type"] = 1,
    ["Track"] = 4
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 42270,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 42570,
    ["Type"] = 1,
    ["Track"] = 4
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 42570,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 43170,
    ["Type"] = 2,
    ["Track"] = 2,
    ["Duration"] = 2400
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 45570,
    ["Type"] = 2,
    ["Track"] = 3,
    ["Duration"] = 1500
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 47895,
    ["Type"] = 1,
    ["Track"] = 4
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 48345,
    ["Type"] = 1,
    ["Track"] = 3
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 48795,
    ["Type"] = 1,
    ["Track"] = 2
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 49245,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 50295,
    ["Type"] = 1,
    ["Track"] = 4
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 50745,
    ["Type"] = 1,
    ["Track"] = 3
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 51195,
    ["Type"] = 1,
    ["Track"] = 2
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 51645,
    ["Type"] = 1,
    ["Track"] = 1
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 52770,
    ["Type"] = 1,
    ["Track"] = 4
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 53220,
    ["Type"] = 1,
    ["Track"] = 3
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 53670,
    ["Type"] = 1,
    ["Track"] = 2
}
v_u_1.HitObjects[#v_u_1.HitObjects + 1] = {
    ["Time"] = 54120,
    ["Type"] = 1,
    ["Track"] = 1
}
return v_u_1;
