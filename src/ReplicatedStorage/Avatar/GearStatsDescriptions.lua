-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:18 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Avatar.GearStats)
local v2 = {}
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict):new():add_table({
    [v1.Type.ColorBlue] = "Increases score for songs with \'Chill\' type.",
    [v1.Type.ColorGreen] = "Increases score for songs with \'Vibe\' type.",
    [v1.Type.ColorPurple] = "Increases score for songs with \'Flow\' type.",
    [v1.Type.ColorRed] = "Increases score for songs with \'Rush\' type.",
    [v1.Type.ColorOrange] = "Increases score for songs with \'Beat\' type.",
    [v1.Type.NoteSpeed] = "Changes the speed at which notes approach.",
    [v1.Type.PerfectTime] = "Changes the timing window to get a perfect hit.",
    [v1.Type.PerfectPoints] = "Changes the base point value of a perfect hit.",
    [v1.Type.GreatTime] = "Changes the timing window to get a great hit.",
    [v1.Type.GreatPoints] = "Changes the base point value of a great hit.",
    [v1.Type.OkayTime] = "Changes the timing window to get an okay hit.",
    [v1.Type.OkayPoints] = "Changes the base point value of an okay hit.",
    [v1.Type.ComboThreshold] = "Changes the threshold at which different combo multipliers are triggered.",
    [v1.Type.ComboMultiplier] = "Changes the value of the combo multiplier on note hits.",
    [v1.Type.ComboBreakMultiplier] = "Changes the percentage of combo lost on miss.",
    [v1.Type.FeverFillRate] = "Changes the fill rate for the fever bar.",
    [v1.Type.FeverMultiplier] = "Changes the value of the fever multiplier on note hits when fever is active.",
    [v1.Type.FeverTime] = "Changes the duration of fever bar activation.",
    [v1.Type.FeverDrainRate] = "Changes the drain effect of fever when a note is missed."
})
v2.get_description_for_stat = function(_, p4) --[[ Name: get_description_for_stat ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return v_u_3:get(p4);
end;
return v2;
