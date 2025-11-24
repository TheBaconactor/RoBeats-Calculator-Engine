-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:08 PM
-- Cached decompilation

local _ = game:GetService("Players")
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.NoteSkinColor)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_7 = require(game.ReplicatedStorage.Shared.Note2DSettings)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_9 = {
    ["Type"] = "GameNoteSkinInfo"
}
v_u_9.new = function(_) --[[ Name: new ]] --[[ Line: 17 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_3, (copy 5): v_u_5, (copy 6): v_u_8, (copy 7): v_u_7, (copy 8): v_u_6 ]]
    local v15 = {
        ["Type"] = v_u_9.Type,
        ["get_slot_notespeed_multiplier"] = function(p10, p11) --[[ Name: get_slot_notespeed_multiplier ]] --[[ Line: 83 ]]
            return p10:get_slot_player_settings(p11):get_note_speed_multiplier();
        end,
        ["get_slot_player_settings_key"] = function(p12, p13, p14) --[[ Name: get_slot_player_settings_key ]] --[[ Line: 120 ]]
            return p12:get_slot_player_settings(p13):get_key(p14);
        end
    }
    local v_u_16 = v_u_1:new()
    v15.set_player_info = function(_, p17, p18, p19, p20, p21, p22) --[[ Name: set_player_info ]] --[[ Line: 23 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_3, (copy 3): v_u_16 ]]
        v_u_4:is_int(p17)
        v_u_4:is_true(p18:count() == 4)
        for v23 = 1, p18:count() do
            v_u_4:is_true(p18:get(v23).Type == v_u_3.Type)
        end;
        v_u_4:is_true(p19:count() == 4)
        for v24 = 1, p19:count() do
            v_u_4:is_true(p19:get(v24).Type == v_u_3.Type)
        end;
        v_u_4:is_int(p20)
        v_u_4:is_table(p21)
        v_u_16:add(p17, {
            ["BaseColorList"] = p18,
            ["FeverColorList"] = p19,
            ["FeverIcon"] = p20,
            ["PlayerSettings"] = p21,
            ["ExtraData"] = p22
        })
    end;
    v15.get_slot_basecolor_list = function(_, p25) --[[ Name: get_slot_basecolor_list ]] --[[ Line: 52 ]]
        --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_9 ]]
        if v_u_16:contains(p25) then
            return v_u_16:get(p25).BaseColorList;
        else
            return v_u_9:get_default_base_color_list();
        end;
    end;
    v15.get_slot_fevercolor_list = function(_, p26) --[[ Name: get_slot_fevercolor_list ]] --[[ Line: 60 ]]
        --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_9 ]]
        if v_u_16:contains(p26) then
            return v_u_16:get(p26).FeverColorList;
        else
            return v_u_9:get_default_fever_color_list();
        end;
    end;
    v15.get_slot_fevericon_effect_from_setting = function(p27, p28) --[[ Name: get_slot_fevericon_effect_from_setting ]] --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_8, (copy 3): v_u_16 ]]
        local v29 = p27:get_slot_player_settings_key(p28, v_u_5.Key.FeverIconDisplay)
        if v29 == v_u_8.FeverIconDisplay.Stars then
            return v_u_8:singleton():get_stars_icon_id();
        elseif v29 == v_u_8.FeverIconDisplay.None then
            return v_u_8:singleton():get_disabled_icon_id();
        elseif v_u_16:contains(p28) then
            return v_u_16:get(p28).FeverIcon;
        else
            return v_u_8:singleton():get_stars_icon_id();
        end;
    end;
    v15.get_slot_display_mode = function(p30, p31) --[[ Name: get_slot_display_mode ]] --[[ Line: 87 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        return p30:get_slot_player_settings_key(p31, v_u_5.Key.NoteDisplayMode);
    end;
    v15.get_slot_note_decal_id = function(p32, p33) --[[ Name: get_slot_note_decal_id ]] --[[ Line: 91 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_5 ]]
        return v_u_7.Skin:get_note_decal_database_id(p32:get_slot_player_settings_key(p33, v_u_5.Key.Note2DSettingsSkin));
    end;
    v15.get_slot_note2d_settings_width = function(p34, p35) --[[ Name: get_slot_note2d_settings_width ]] --[[ Line: 100 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        return p34:get_slot_player_settings_key(p35, v_u_5.Key.Note2DSettingsWidth);
    end;
    v15.get_slot_note2d_setting_position = function(p36, p37) --[[ Name: get_slot_note2d_setting_position ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        return p36:get_slot_player_settings_key(p37, v_u_5.Key.Note2DSettingsPosition);
    end;
    v15.get_slot_note2d_setting_background = function(p38, p39) --[[ Name: get_slot_note2d_setting_background ]] --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        return p38:get_slot_player_settings_key(p39, v_u_5.Key.Note2DSettingsBackground);
    end;
    v15.get_slot_player_settings = function(_, p40) --[[ Name: get_slot_player_settings ]] --[[ Line: 112 ]]
        --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_5 ]]
        if v_u_16:contains(p40) then
            return v_u_16:get(p40).PlayerSettings;
        else
            return v_u_5:new();
        end;
    end;
    v15.add_playerblob_to_slot = function(p41, p42, p43) --[[ Name: add_playerblob_to_slot ]] --[[ Line: 124 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_5, (ref 3): v_u_6 ]]
        local v44 = v_u_3:note_basecolor_list_from_playerblob(p42)
        local v45 = v_u_3:note_fevercolor_list_from_playerblob(p42)
        local v46 = v_u_5:new()
        v46:load_from_json_str(v_u_6:get_player_settings_str(p42))
        p41:set_player_info(p43, v44, v45, p42.FeverIcon, v46, {})
    end;
    v15.add_default_to_slot = function(p47, p48) --[[ Name: add_default_to_slot ]] --[[ Line: 144 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_8, (ref 3): v_u_5 ]]
        p47:set_player_info(p48, v_u_9:get_default_base_color_list(), v_u_9:get_default_fever_color_list(), v_u_8:singleton():get_stars_icon_id(), v_u_5:new(), {})
    end;
    v15.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 155 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        local v49 = {}
        for v50 = 1, 4 do
            if v_u_16:contains(v50) then
                local v51 = v_u_16:get(v50)
                local v52 = {}
                local v53 = {}
                for v54 = 1, 4 do
                    v52[v54] = v51.BaseColorList:get(v54):to_table()
                    v53[v54] = v51.FeverColorList:get(v54):to_table()
                end;
                v49[v50] = {
                    ["BaseColorList"] = v52,
                    ["FeverColorList"] = v53,
                    ["FeverIcon"] = v51.FeverIcon,
                    ["PlayerSettingsJson"] = v51.PlayerSettings:to_json(),
                    ["ExtraData"] = v51.ExtraData
                }
            else
                v49[v50] = 0
            end;
        end;
        return v49;
    end;
    return v15;
end;
v_u_9.from_table = function(_, p55) --[[ Name: from_table ]] --[[ Line: 185 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_5 ]]
    local v56 = v_u_9:new()
    for v57 = 1, 4 do
        if p55[v57] ~= 0 then
            local v58 = p55[v57]
            local v59 = v_u_2:new()
            local v60 = v_u_2:new()
            for v61 = 1, 4 do
                v59:push_back(v_u_3:from_table(v58.BaseColorList[v61]))
                v60:push_back(v_u_3:from_table(v58.FeverColorList[v61]))
            end;
            local v62 = v_u_5:new()
            v62:load_from_json_str(v58.PlayerSettingsJson)
            v56:set_player_info(v57, v59, v60, v58.FeverIcon, v62, v58.ExtraData)
        end;
    end;
    return v56;
end;
local v_u_63 = v_u_2:new()
for _ = 1, 4 do
    v_u_63:push_back(v_u_3:get_default_base_color())
end;
v_u_9.get_default_base_color_list = function(_) --[[ Name: get_default_base_color_list ]] --[[ Line: 218 ]]
    --[[ Upvalues: (copy 1): v_u_63 ]]
    return v_u_63;
end;
local v_u_64 = v_u_2:new()
for _ = 1, 4 do
    v_u_64:push_back(v_u_3:get_default_fever_color())
end;
v_u_9.get_default_fever_color_list = function(_) --[[ Name: get_default_fever_color_list ]] --[[ Line: 226 ]]
    --[[ Upvalues: (copy 1): v_u_64 ]]
    return v_u_64;
end;
return v_u_9;
