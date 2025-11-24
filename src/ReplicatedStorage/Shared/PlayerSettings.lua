-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:06 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugOut)
local _ = game:GetService("Players")
local s_HttpService_0 = game:GetService("HttpService")
local v_u_4 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_8 = require(game.ReplicatedStorage.Shared.Note2DSettings)
local v_u_9 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_11 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_12 = require(game.ReplicatedStorage.Shared.NoteResultPositionSetting)
local v_u_13 = require(game.ReplicatedStorage.Shared.NoteResultSpreadSetting)
local v14 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_15 = nil
local v_u_16 = nil
v14:require_shared(function() --[[ Line: 20 ]]
    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16 ]]
    v_u_15 = require(game.ReplicatedStorage.LocalShared.CharacterCulling)
    v_u_16 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
end)
local v_u_17 = {
    ["Key"] = {
        ["HitSFX"] = "HitSFX",
        ["BGM"] = "BGM",
        ["PCCharacterCulling"] = "PCCharacterCulling",
        ["MobileCharacterCulling"] = "MobileCharacterCulling",
        ["MobileFullScreenUI"] = "MobileFullScreenUI",
        ["KeybindMatchmakingChat"] = string.format("Keybind_%d", v_u_1.KEY_MENU_MATCHMAKING_CHAT_FOCUS),
        ["KeybindChatWindow"] = string.format("Keybind_%d", v_u_1.KEY_CHAT_WINDOW_FOCUS),
        ["KeybindTrack1"] = string.format("Keybind_%d", v_u_1.KEY_TRACK1),
        ["KeybindTrack2"] = string.format("Keybind_%d", v_u_1.KEY_TRACK2),
        ["KeybindTrack3"] = string.format("Keybind_%d", v_u_1.KEY_TRACK3),
        ["KeybindTrack4"] = string.format("Keybind_%d", v_u_1.KEY_TRACK4),
        ["KeybindPowerbarTrigger"] = string.format("Keybind_%d", v_u_1.KEY_POWERBAR_TRIGGER),
        ["BrightnessSettings"] = "Brightness",
        ["NoteOffset"] = "NoteOffset",
        ["RadioEnabled"] = "Radio",
        ["NoteSpeed"] = "NoteSpeed",
        ["HeldNoteTransparent"] = "HeldAlpha",
        ["FixedNoteSpeed"] = "FxNS",
        ["ShowComboDisplay"] = "ShCombDsp",
        ["NoteDisplayMode"] = "NDM",
        ["Note2DSettingsSkin"] = "N2D_S",
        ["Note2DSettingsWidth"] = "N2D_W",
        ["Note2DSettingsPosition"] = "N2D_P",
        ["ShowHeldNoteTail"] = "HNT_S",
        ["ShowAllSongs"] = "SAS",
        ["AutoEquipBestLoadout"] = "AEBL",
        ["Note2DSettingsBackground"] = "N2D_B",
        ["FeverIconDisplay"] = "FDI",
        ["MatchMode"] = "MM",
        ["SelectedGameStage"] = "SGS",
        ["GameShowCharacters"] = "GSC",
        ["ArtistEventUseStage"] = "AEUS",
        ["ShowGameMissionDisplay"] = "SGMD",
        ["NoteResultPositionSetting"] = "NRP",
        ["NoteResultSpreadSetting"] = "NRS",
        ["ControllerTrack1List"] = "CT1",
        ["ControllerTrack2List"] = "CT2",
        ["ControllerTrack3List"] = "CT3",
        ["ControllerTrack4List"] = "CT4",
        ["ControllerShowCursorList"] = "CCL",
        ["LoadoutNames"] = "LN"
    }
}
local v18 = v_u_2:new()
local v_u_19 = v_u_15
local v_u_20 = v_u_16
for _, v21 in pairs(v_u_17.Key) do
    if v18:contains(v21) then
        v_u_3:errf("PlayerSettings duplicate key(%s)", (tostring(v21)))
    end;
    v18:add_set(v21)
end;
v_u_17.new = function(_) --[[ Name: new ]] --[[ Line: 80 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): s_HttpService_0, (copy 3): v_u_17, (ref 4): v_u_19, (copy 5): v_u_4, (copy 6): v_u_7, (copy 7): v_u_8, (copy 8): v_u_10, (copy 9): v_u_11, (ref 10): v_u_20, (copy 11): v_u_12, (copy 12): v_u_13, (copy 13): v_u_9 ]]
    local v23 = {
        ["cons"] = function(p22) --[[ Name: cons ]] --[[ Line: 85 ]]
            p22:initialize_with_defaults()
        end
    }
    local v_u_24 = v_u_2:new()
    v23.load_from_json_str = function(_, p_u_25) --[[ Name: load_from_json_str ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): s_HttpService_0, (copy 2): v_u_24 ]]
        local v_u_26 = nil
        pcall(function() --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): s_HttpService_0, (copy 3): p_u_25 ]]
            v_u_26 = s_HttpService_0:JSONDecode(p_u_25)
        end)
        if v_u_26 ~= nil then
            for v27, v28 in pairs(v_u_26) do
                if v_u_24:contains(v27) and typeof(v28) == typeof(v_u_24:get(v27)) then
                    v_u_24:add(v27, v28)
                end;
            end;
        end;
    end;
    v23.initialize_with_defaults = function(p29) --[[ Name: initialize_with_defaults ]] --[[ Line: 103 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_19, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): v_u_8, (ref 6): v_u_10, (ref 7): v_u_11, (ref 8): v_u_20, (ref 9): v_u_12, (ref 10): v_u_13 ]]
        p29:initialize_key(v_u_17.Key.HitSFX, true)
        p29:initialize_key(v_u_17.Key.BGM, true)
        p29:initialize_key(v_u_17.Key.PCCharacterCulling, v_u_19.Mode.Medium)
        p29:initialize_key(v_u_17.Key.MobileCharacterCulling, v_u_19.Mode.Low)
        p29:initialize_key(v_u_17.Key.KeybindMatchmakingChat, -1)
        p29:initialize_key(v_u_17.Key.KeybindChatWindow, -1)
        p29:initialize_key(v_u_17.Key.KeybindTrack1, -1)
        p29:initialize_key(v_u_17.Key.KeybindTrack2, -1)
        p29:initialize_key(v_u_17.Key.KeybindTrack3, -1)
        p29:initialize_key(v_u_17.Key.KeybindTrack4, -1)
        p29:initialize_key(v_u_17.Key.KeybindPowerbarTrigger, -1)
        p29:initialize_key(v_u_17.Key.BrightnessSettings, v_u_4.Dark)
        p29:initialize_key(v_u_17.Key.MobileFullScreenUI, true)
        p29:initialize_key(v_u_17.Key.NoteOffset, 0)
        p29:initialize_key(v_u_17.Key.RadioEnabled, false)
        p29:initialize_key(v_u_17.Key.NoteSpeed, v_u_17:get_note_speed_default())
        p29:initialize_key(v_u_17.Key.HeldNoteTransparent, true)
        p29:initialize_key(v_u_17.Key.FixedNoteSpeed, false)
        p29:initialize_key(v_u_17.Key.ShowComboDisplay, true)
        p29:initialize_key(v_u_17.Key.NoteDisplayMode, v_u_7.Default)
        p29:initialize_key(v_u_17.Key.Note2DSettingsSkin, v_u_8.Skin.Default)
        p29:initialize_key(v_u_17.Key.Note2DSettingsWidth, v_u_8.Width.Default)
        p29:initialize_key(v_u_17.Key.Note2DSettingsPosition, v_u_8.Position.Default)
        p29:initialize_key(v_u_17.Key.ShowHeldNoteTail, false)
        p29:initialize_key(v_u_17.Key.ShowAllSongs, false)
        p29:initialize_key(v_u_17.Key.AutoEquipBestLoadout, true)
        p29:initialize_key(v_u_17.Key.Note2DSettingsBackground, v_u_8.Background.Default)
        p29:initialize_key(v_u_17.Key.FeverIconDisplay, v_u_10.FeverIconDisplay.Stars)
        p29:initialize_key(v_u_17.Key.MatchMode, v_u_11.Casual)
        p29:initialize_key(v_u_17.Key.SelectedGameStage, v_u_20:singleton():get_default_stage_id())
        p29:initialize_key(v_u_17.Key.GameShowCharacters, true)
        p29:initialize_key(v_u_17.Key.ArtistEventUseStage, true)
        p29:initialize_key(v_u_17.Key.ShowGameMissionDisplay, true)
        p29:initialize_key(v_u_17.Key.NoteResultPositionSetting, v_u_12.Default)
        p29:initialize_key(v_u_17.Key.NoteResultSpreadSetting, v_u_13.Default)
        p29:initialize_key(v_u_17.Key.ControllerTrack1List, {})
        p29:initialize_key(v_u_17.Key.ControllerTrack2List, {})
        p29:initialize_key(v_u_17.Key.ControllerTrack3List, {})
        p29:initialize_key(v_u_17.Key.ControllerTrack4List, {})
        p29:initialize_key(v_u_17.Key.ControllerShowCursorList, {})
        p29:initialize_key(v_u_17.Key.LoadoutNames, {})
    end;
    v23.initialize_key = function(p30, p31, p32) --[[ Name: initialize_key ]] --[[ Line: 158 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_17, (copy 3): v_u_24 ]]
        v_u_9:is_enum_member(p31, v_u_17.Key)
        if v_u_24:contains(p31) ~= true then
            v_u_24:add(p31, p32)
        end;
        return p30:get_key(p31);
    end;
    v23.get_key = function(_, p33) --[[ Name: get_key ]] --[[ Line: 166 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_17, (copy 3): v_u_24 ]]
        v_u_9:is_enum_member(p33, v_u_17.Key)
        return v_u_24:get(p33);
    end;
    v23.set_key = function(_, p34, p35) --[[ Name: set_key ]] --[[ Line: 171 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_17, (copy 3): v_u_24 ]]
        v_u_9:is_enum_member(p34, v_u_17.Key)
        v_u_9:is_true(typeof(p35) == typeof(v_u_24:get(p34)))
        v_u_24:add(p34, p35)
    end;
    v23.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 177 ]]
        --[[ Upvalues: (copy 1): v_u_24 ]]
        local v36 = {}
        for v37, v38 in v_u_24:key_itr() do
            v36[v37] = v38
        end;
        return v36;
    end;
    v23.to_json = function(p_u_39) --[[ Name: to_json ]] --[[ Line: 185 ]]
        --[[ Upvalues: (ref 1): s_HttpService_0 ]]
        local v_u_40 = "{}"
        pcall(function() --[[ Line: 187 ]]
            --[[ Upvalues: (ref 1): v_u_40, (ref 2): s_HttpService_0, (copy 3): p_u_39 ]]
            v_u_40 = s_HttpService_0:JSONEncode(p_u_39:to_table())
        end)
        return v_u_40;
    end;
    v23.get_note_speed_multiplier = function(p41) --[[ Name: get_note_speed_multiplier ]] --[[ Line: 193 ]]
        --[[ Upvalues: (ref 1): v_u_17 ]]
        return v_u_17:get_multiplier_for_note_speed(p41:get_key(v_u_17.Key.NoteSpeed));
    end;
    v23:cons()
    return v23;
end;
v_u_17.apply_new_player_settings = function(_, _) end;
v_u_17.get_note_speed_min = function(_) --[[ Name: get_note_speed_min ]] --[[ Line: 205 ]]
    return 0;
end;
v_u_17.get_note_speed_max = function(_) --[[ Name: get_note_speed_max ]] --[[ Line: 206 ]]
    return 100;
end;
v_u_17.get_note_speed_default = function(_) --[[ Name: get_note_speed_default ]] --[[ Line: 207 ]]
    --[[ Upvalues: (copy 1): v_u_17 ]]
    return (v_u_17:get_note_speed_max() - v_u_17:get_note_speed_min()) * 0.5 + v_u_17:get_note_speed_min();
end;
v_u_17.get_multiplier_for_note_speed = function(_, p42) --[[ Name: get_multiplier_for_note_speed ]] --[[ Line: 208 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_17, (copy 3): v_u_6 ]]
    local v43 = v_u_5:clamp(p42, v_u_17:get_note_speed_min(), v_u_17:get_note_speed_max())
    if v43 < v_u_17:get_note_speed_default() then
        return v_u_6:YForPointOf2PtLineP1P2X(v_u_17:get_note_speed_min(), 5, v_u_17:get_note_speed_default(), 1, v43);
    else
        return v_u_6:YForPointOf2PtLineP1P2X(v_u_17:get_note_speed_default(), 1, v_u_17:get_note_speed_max(), 0.2, v43);
    end;
end;
v_u_17.track_enum_to_controller_track_setting = function(_, p44) --[[ Name: track_enum_to_controller_track_setting ]] --[[ Line: 217 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_17 ]]
    if p44 == v_u_1.KEY_TRACK1 then
        return v_u_17.Key.ControllerTrack1List;
    elseif p44 == v_u_1.KEY_TRACK2 then
        return v_u_17.Key.ControllerTrack2List;
    elseif p44 == v_u_1.KEY_TRACK3 then
        return v_u_17.Key.ControllerTrack3List;
    else
        return v_u_17.Key.ControllerTrack4List;
    end;
end;
v_u_17.server_validate_client_updated_player_settings = function(_, p45, p46) --[[ Name: server_validate_client_updated_player_settings ]] --[[ Line: 229 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_17 ]]
    local function f_track_list_okay(p47) --[[ Name: track_list_okay ]] --[[ Line: 231 ]]
        --[[ Upvalues: (ref 1): v_u_3 ]]
        if #p47 > 32 then
            v_u_3:warnf("PlayerSettings:server_validate_client_updated_player_settings() #list_tab > 32")
            return false;
        else
            for v48 = 1, #p47 do
                if typeof(p47[v48]) ~= "number" then
                    v_u_3:warnf("PlayerSettings:server_validate_client_updated_player_settings() typeof(list_tab[%d]) ~= number", v48)
                    return false;
                end;
            end;
            return true;
        end;
    end;
    if f_track_list_okay(p46:get_key(v_u_17.Key.ControllerTrack1List)) == true then
        if f_track_list_okay(p46:get_key(v_u_17.Key.ControllerTrack2List)) == true then
            if f_track_list_okay(p46:get_key(v_u_17.Key.ControllerTrack3List)) == true then
                if f_track_list_okay(p46:get_key(v_u_17.Key.ControllerTrack4List)) == true then
                    if f_track_list_okay(p46:get_key(v_u_17.Key.ControllerShowCursorList)) == true then
                        local v49 = p45:get_key(v_u_17.Key.LoadoutNames)
                        local v50 = p46:get_key(v_u_17.Key.LoadoutNames)
                        if #v49 == #v50 then
                            for v51 = 1, #v49 do
                                if v49[v51] ~= v50[v51] then
                                    v_u_3:warnf("PlayerSettings:server_validate_client_updated_player_settings() loadout_names_pre[%d] ~= updated_loadout_names[%d]", v51, v51)
                                    return false;
                                end;
                            end;
                            return true;
                        else
                            v_u_3:warnf("PlayerSettings:server_validate_client_updated_player_settings() #loadout_names_pre ~= #updated_loadout_names")
                            return false;
                        end;
                    else
                        return;
                    end;
                else
                    return;
                end;
            else
                return;
            end;
        else
            return;
        end;
    else
        return;
    end;
end;
return v_u_17;
