-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:10 PM
-- Cached decompilation

local _ = game:GetService("Players")
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
local v4 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_5 = nil
v4:require_shared(function() --[[ Line: 8 ]]
    --[[ Upvalues: (ref 1): v_u_5 ]]
    v_u_5 = require(game.ReplicatedStorage.Shared.PlayerSettings)
end)
local v_u_8 = {
    ["Skin"] = f_create_enum("Note Skin", v18, function(p6) --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_3 ]]
        p6.get_note_decal_database_id = function(_, p7) --[[ Name: get_note_decal_database_id ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_3 ]]
            return p7 == v_u_8.Skin.Circles and 1 or (p7 == v_u_8.Skin.Bars and 2 or (p7 == v_u_8.Skin.Arrows and 3 or (p7 == v_u_8.Skin["Arrows (FNF)"] and 4 or (p7 == v_u_8.Skin.Diamonds and 5 or v_u_3:singleton():get_default_notedecal_id()))));
        end;
    end),
    ["Width"] = f_create_enum("Note Width", v19),
    ["Position"] = f_create_enum("Note Position", v20),
    ["Background"] = f_create_enum("Track Background", v21)
}
local function f_create_enum(p_u_9, p10, p11) --[[ Name: create_enum ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    local v12 = v_u_1:new()
    local v_u_13 = v_u_1:new()
    local v_u_14 = v_u_2:new()
    for v15, v16 in pairs(p10) do
        v12:add(v15, v16)
        v_u_13:add(v16, v15)
        v_u_14:push_back(v16)
    end;
    v_u_2:sort_fast(v_u_14)
    p10.get_setting_name = function(_) --[[ Name: get_setting_name ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): p_u_9 ]]
        return p_u_9;
    end;
    p10.get_name = function(_, p17) --[[ Name: get_name ]] --[[ Line: 26 ]]
        --[[ Upvalues: (copy 1): v_u_13 ]]
        return v_u_13:get(p17);
    end;
    p10.key_itr = function(_) --[[ Name: key_itr ]] --[[ Line: 27 ]]
        --[[ Upvalues: (copy 1): v_u_14 ]]
        return v_u_14:key_itr();
    end;
    if p11 then
        p11(p10)
    end;
    return p10;
end;
local v18 = {
    ["Default"] = 1,
    ["Circles"] = 2,
    ["Bars"] = 3,
    ["Arrows"] = 4,
    ["Arrows (FNF)"] = 5,
    ["Diamonds"] = 6
}
local v19 = {
    ["Default"] = 1,
    ["A Bit Wider (x1.15)"] = 2,
    ["Wider (x1.25)"] = 3,
    ["Even Wider (x1.5)"] = 4,
    ["Widest (x2)"] = 5,
    ["A Bit More Narrow (x0.85)"] = 6,
    ["Narrow (x0.75)"] = 7,
    ["Narrowest (x0.5)"] = 8
}
local v20 = {
    ["Default"] = 1,
    ["A Bit Higher (x1.25)"] = 2,
    ["Higher (x1.5)"] = 3,
    ["Even Higher (x2)"] = 4,
    ["Highest (x3)"] = 5,
    ["Mid-Screen"] = 6,
    ["Lowest"] = 7
}
local v21 = {
    ["Default"] = 1,
    ["Dark"] = 2,
    ["Transparent"] = 3
}
v_u_8.enum_class_to_playersettings_key = function(_, p22) --[[ Name: enum_class_to_playersettings_key ]] --[[ Line: 87 ]]
    --[[ Upvalues: (copy 1): v_u_8, (ref 2): v_u_5 ]]
    if p22 == v_u_8.Skin then
        return v_u_5.Key.Note2DSettingsSkin;
    end;
    if p22 == v_u_8.Width then
        return v_u_5.Key.Note2DSettingsWidth;
    end;
    if p22 == v_u_8.Position then
        return v_u_5.Key.Note2DSettingsPosition;
    end;
    if p22 == v_u_8.Background then
        return v_u_5.Key.Note2DSettingsBackground;
    end;
end;
return v_u_8;
