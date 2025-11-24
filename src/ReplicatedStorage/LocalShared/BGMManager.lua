-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:00 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.AssertType)
return {
    ["BGM_LOBBY"] = "rbxassetid://847123591",
    ["BGM_MATCHMAKING"] = "rbxassetid://847123756",
    ["BGM_SONGEND"] = "rbxassetid://847124558",
    ["BGM_SHOP"] = "rbxassetid://847124722",
    ["new"] = function(_, p_u_9) --[[ Name: new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_6, (copy 4): v_u_5, (copy 5): v_u_8, (copy 6): v_u_4, (copy 7): v_u_2, (copy 8): v_u_7 ]]
        local v_u_10 = {}
        local l_Folder_0 = Instance.new("Folder", game.Workspace)
        l_Folder_0.Name = v_u_3:gen_name("BGMManager")
        local v_u_11 = nil
        local v_u_12 = v_u_1:new()
        v_u_10.get_playing_bgm_key = function(_) --[[ Name: get_playing_bgm_key ]] --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11;
        end;
        local v_u_13 = nil
        local v_u_14 = nil
        local v_u_15 = ""
        local v_u_16 = nil
        local v_u_17 = false
        local function f_cons() --[[ Name: cons ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_14, (copy 2): l_Folder_0, (copy 3): v_u_10, (ref 4): v_u_16 ]]
            v_u_14 = Instance.new("Sound", l_Folder_0)
            v_u_14.Playing = false
            v_u_14.Looped = true
            v_u_14.Volume = 0
            v_u_14.DidLoop:Connect(function() --[[ Line: 40 ]]
                --[[ Upvalues: (ref 1): v_u_10 ]]
                v_u_10:preview_sound_on_loop()
            end)
            v_u_14.Name = "_preview_sound"
            v_u_16 = Instance.new("Sound", l_Folder_0)
            v_u_16.Playing = false
            v_u_16.Looped = true
            v_u_16.Volume = 0
            v_u_16.Name = "_club_sound"
        end;
        v_u_10.play_bgm = function(_, p18) --[[ Name: play_bgm ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_11, (copy 3): v_u_12, (copy 4): l_Folder_0 ]]
            v_u_17 = false
            if p18 == v_u_11 then
                return;
            else
                v_u_11 = p18
                if p18 ~= nil then
                    if v_u_12:contains(p18) == false then
                        local l_Sound_0 = Instance.new("Sound", l_Folder_0)
                        l_Sound_0.SoundId = p18
                        l_Sound_0.Playing = true
                        l_Sound_0.Looped = true
                        l_Sound_0.Volume = 0
                        l_Sound_0.Name = p18
                        v_u_12:add(p18, l_Sound_0)
                    end;
                end;
            end;
        end;
        v_u_10.is_playing_club_bgm = function(_) --[[ Name: is_playing_club_bgm ]] --[[ Line: 77 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17;
        end;
        v_u_10.play_club_bgm = function(p19) --[[ Name: play_club_bgm ]] --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_16 ]]
            if v_u_17 ~= true then
                p19:sync_club_bgm_state()
                v_u_16.Volume = 0
            end;
            v_u_17 = true
        end;
        local v_u_20 = v_u_6:singleton():get_default_audio_volume()
        local v_u_21 = v_u_20
        v_u_10.sync_club_bgm_state = function(_) --[[ Name: sync_club_bgm_state ]] --[[ Line: 89 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_6, (ref 3): v_u_16, (ref 4): v_u_3, (ref 5): v_u_5, (ref 6): v_u_21, (copy 7): v_u_20 ]]
            local v22, v23, _, _ = p_u_9._dance_club_manager:get_current_song_info()
            if v_u_6:singleton():contains_key(v22) then
                local v24 = v_u_6:singleton():get_audio_assetid_for_key(v22)
                if v_u_16.SoundId ~= v24 then
                    v_u_16.Playing = false
                    v_u_16.SoundId = v24
                    v_u_16.Volume = 0
                    v_u_16.TimePosition = 0
                    v_u_16.Playing = true
                end;
                if math.abs(v_u_16.TimePosition - v23) > 0.5 then
                    if v_u_3:is_dev_build() then
                        v_u_5:puts("BGMManager:sync_club_bgm_state sync _club_sound(Playing=%s, Volume=%.2f, TimePosition=%.2f) to (%.2f)", tostring(v_u_16.Playing), v_u_16.Volume, v_u_16.TimePosition, v23)
                    end;
                    v_u_16.TimePosition = v23
                end;
                v_u_21 = v_u_6:singleton():get_audio_volume_for_key(v22)
            else
                v_u_16.SoundId = ""
                v_u_16.Volume = 0
                v_u_21 = v_u_20
            end;
        end;
        local v_u_35 = {
            ["new"] = function(_, p_u_25, p_u_26, p_u_27) --[[ Name: new ]] --[[ Line: 122 ]]
                local v28 = {}
                v28.get_override_assetid = function(_) --[[ Name: get_override_assetid ]] --[[ Line: 125 ]]
                    --[[ Upvalues: (ref 1): p_u_26 ]]
                    return p_u_26;
                end;
                v28.end_on_finish = function(_) --[[ Name: end_on_finish ]] --[[ Line: 126 ]]
                    --[[ Upvalues: (ref 1): p_u_27 ]]
                    return p_u_27;
                end;
                v28.get_songkey = function(_) --[[ Name: get_songkey ]] --[[ Line: 127 ]]
                    --[[ Upvalues: (ref 1): p_u_25 ]]
                    return p_u_25;
                end;
                v28.set_songkey = function(p29, p30) --[[ Name: set_songkey ]] --[[ Line: 129 ]]
                    --[[ Upvalues: (ref 1): p_u_25 ]]
                    p_u_25 = p30
                    return p29;
                end;
                v28.set_override_assetid = function(p31, p32) --[[ Name: set_override_assetid ]] --[[ Line: 130 ]]
                    --[[ Upvalues: (ref 1): p_u_26 ]]
                    p_u_26 = p32
                    return p31;
                end;
                v28.set_end_on_finish = function(p33, p34) --[[ Name: set_end_on_finish ]] --[[ Line: 131 ]]
                    --[[ Upvalues: (ref 1): p_u_27 ]]
                    p_u_27 = p34
                    return p33;
                end;
                return v28;
            end
        }
        local v_u_36 = v_u_8:new()
        local v_u_37 = v_u_20
        v_u_10.get_preview_songkey_stack = function(_) --[[ Name: get_preview_songkey_stack ]] --[[ Line: 138 ]]
            --[[ Upvalues: (copy 1): v_u_36 ]]
            return v_u_36;
        end;
        v_u_10.get_preview_songkey = function(_) --[[ Name: get_preview_songkey ]] --[[ Line: 139 ]]
            --[[ Upvalues: (copy 1): v_u_36, (ref 2): v_u_6 ]]
            if v_u_36:count() > 0 then
                return v_u_36:back():get_songkey();
            else
                return v_u_6:invalid_songkey();
            end;
        end;
        local function f_update_preview_assetid_and_volume_to_stack_top() --[[ Name: update_preview_assetid_and_volume_to_stack_top ]] --[[ Line: 147 ]]
            --[[ Upvalues: (copy 1): v_u_36, (ref 2): v_u_13, (ref 3): v_u_37, (ref 4): v_u_6, (copy 5): v_u_20 ]]
            if v_u_36:count() > 0 then
                local v38 = v_u_36:back()
                if v38:get_override_assetid() == nil then
                    if v_u_6:singleton():contains_key(v38:get_songkey()) then
                        v_u_13 = v_u_6:singleton():get_audio_assetid_for_key(v38:get_songkey())
                        v_u_37 = v_u_6:singleton():get_audio_volume_for_key(v38:get_songkey())
                    else
                        v_u_13 = nil
                        v_u_37 = v_u_20
                    end;
                else
                    v_u_13 = v38:get_override_assetid()
                    v_u_37 = 1
                    return;
                end;
            else
                v_u_13 = nil
                v_u_37 = v_u_20
                return;
            end;
        end;
        v_u_10.begin_preview_songkey = function(_, p39, p40, p41) --[[ Name: begin_preview_songkey ]] --[[ Line: 171 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_36, (ref 3): v_u_5, (copy 4): v_u_35, (copy 5): f_update_preview_assetid_and_volume_to_stack_top ]]
            if p41 == nil then
                p41 = false
            end;
            if p39 == nil then
                p39 = v_u_6:invalid_songkey()
            end;
            v_u_36:remove_if(function(p42) --[[ Line: 175 ]]
                --[[ Upvalues: (ref 1): v_u_5 ]]
                if not p42:end_on_finish() then
                    return false;
                end;
                v_u_5:puts("remove end_on_finish bgm stack element")
                return true;
            end)
            local v43 = v_u_35:new(p39, p40, p41)
            v_u_36:push_back(v43)
            f_update_preview_assetid_and_volume_to_stack_top()
            return v43;
        end;
        v_u_10.preview_songkey = function(p44, p45, p46, p47) --[[ Name: preview_songkey ]] --[[ Line: 190 ]]
            --[[ Upvalues: (copy 1): v_u_36, (copy 2): f_update_preview_assetid_and_volume_to_stack_top ]]
            if p47 == nil then
                p47 = false
            end;
            if v_u_36:count() == 0 then
                p44:begin_preview_songkey(p45, p46, p47)
            else
                local v48 = v_u_36:back()
                v48:set_songkey(p45)
                v48:set_override_assetid(p46)
                v48:set_end_on_finish(p47)
                f_update_preview_assetid_and_volume_to_stack_top()
            end;
        end;
        v_u_10.stop_song_preview = function(_, p49) --[[ Name: stop_song_preview ]] --[[ Line: 204 ]]
            --[[ Upvalues: (copy 1): v_u_36, (ref 2): v_u_5, (copy 3): f_update_preview_assetid_and_volume_to_stack_top ]]
            if p49 == nil then
                v_u_36:pop_back()
            elseif v_u_36:contains(p49) then
                v_u_36:remove(p49)
            elseif v_u_36:count() > 0 then
                v_u_5:warnf("BGSMManager:stop_song_preview _preview_songkey_stack(%d) does not contain element, popping back", v_u_36:count())
                v_u_36:pop_back()
            end;
            f_update_preview_assetid_and_volume_to_stack_top()
        end;
        v_u_10.preview_sound_on_loop = function(p50) --[[ Name: preview_sound_on_loop ]] --[[ Line: 221 ]]
            --[[ Upvalues: (copy 1): v_u_36 ]]
            for v51 = v_u_36:count(), 1, -1 do
                local v52 = v_u_36:get(v51)
                if v52:end_on_finish() then
                    p50:stop_song_preview(v52)
                    return;
                end;
            end;
        end;
        v_u_10.stop_all_song_preview = function(_) --[[ Name: stop_all_song_preview ]] --[[ Line: 231 ]]
            --[[ Upvalues: (copy 1): v_u_36, (ref 2): v_u_13, (ref 3): v_u_37, (copy 4): v_u_20 ]]
            v_u_36:clear()
            v_u_13 = nil
            v_u_37 = v_u_20
        end;
        v_u_10.get_previewing_assetid = function(_) --[[ Name: get_previewing_assetid ]] --[[ Line: 237 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            return v_u_13;
        end;
        v_u_10.is_preview_song_loading = function(p53) --[[ Name: is_preview_song_loading ]] --[[ Line: 241 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            local v54
            if p53:get_previewing_assetid() == nil then
                v54 = false
            else
                v54 = v_u_14.IsLoaded ~= true
            end;
            return v54;
        end;
        v_u_10.is_preview_transitioning = function(_) --[[ Name: is_preview_transitioning ]] --[[ Line: 245 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_15 ]]
            local v55
            if v_u_13 == nil then
                v55 = false
            else
                v55 = v_u_15 ~= v_u_13
            end;
            return v55;
        end;
        v_u_10.stop_bgm = function(p56) --[[ Name: stop_bgm ]] --[[ Line: 251 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            p56:play_bgm(nil)
            p56:stop_all_song_preview()
            v_u_17 = false
        end;
        local function _() --[[ Name: test_preview_song_over_timelength ]] --[[ Line: 258 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): v_u_10, (ref 3): v_u_14, (ref 4): v_u_5 ]]
            if v_u_13 ~= nil and (v_u_10:is_preview_song_loading() ~= true and v_u_14.TimeLength > 0) then
                if v_u_14.TimePosition > v_u_14.TimeLength then
                    v_u_14.TimePosition = 0
                    v_u_14.Playing = true
                    v_u_5:puts("BGMManager:test_preview_song_over_timelength activate")
                end;
                if v_u_14.Playing ~= true then
                    v_u_14.Playing = true
                end;
            end;
        end;
        local v_u_57 = false
        v_u_10.force_mute_bgm = function(_, p58) --[[ Name: force_mute_bgm ]] --[[ Line: 272 ]]
            --[[ Upvalues: (ref 1): v_u_57 ]]
            v_u_57 = p58
        end;
        v_u_10.update = function(p59, p60) --[[ Name: update ]] --[[ Line: 276 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_4, (ref 3): v_u_57, (ref 4): v_u_37, (copy 5): v_u_20, (ref 6): v_u_2, (ref 7): v_u_13, (ref 8): v_u_15, (ref 9): v_u_14, (ref 10): v_u_3, (copy 11): v_u_10, (ref 12): v_u_5, (ref 13): v_u_7, (copy 14): v_u_12, (ref 15): v_u_11, (ref 16): v_u_17, (ref 17): v_u_21, (ref 18): v_u_16 ]]
            local v61 = p_u_9._player_settings_manager:get_key(v_u_4.Key.BGM) ~= true or v_u_57 == true
            local v62 = 0.25 * (v_u_37 / v_u_20)
            local v63 = v62 * v_u_2:sec_to_tick(0.5) * p60
            if v_u_13 == nil then
                if v_u_14.Volume > 0 then
                    v_u_14.Volume = v_u_3:clamp(v_u_14.Volume - v63, 0, v62)
                    if v_u_14.Volume <= 0 then
                        v_u_14.Playing = false
                        v_u_15 = ""
                    end;
                end;
            else
                v61 = true
                if v_u_15 == v_u_13 then
                    v_u_14.Volume = v_u_3:clamp(v_u_14.Volume + v63, 0, v62)
                elseif v_u_14.Volume > 0 then
                    v_u_14.Volume = v_u_3:clamp(v_u_14.Volume - v63, 0, v62)
                else
                    v_u_14.SoundId = v_u_13
                    v_u_15 = v_u_13
                    v_u_14.Playing = true
                end;
                if v_u_13 ~= nil and (v_u_10:is_preview_song_loading() ~= true and v_u_14.TimeLength > 0) then
                    if v_u_14.TimePosition > v_u_14.TimeLength then
                        v_u_14.TimePosition = 0
                        v_u_14.Playing = true
                        v_u_5:puts("BGMManager:test_preview_song_over_timelength activate")
                    end;
                    if v_u_14.Playing ~= true then
                        v_u_14.Playing = true
                    end;
                end;
            end;
            if v_u_3:is_dev_build() and (p_u_9._menus:top_menu_swallows_input() == false and p_u_9._input:control_just_pressed(v_u_7.KEY_DEBUG_2)) then
                v_u_5:puts(p59:get_debug_string())
            end;
            local v64 = 0.125 * v_u_2:sec_to_tick(1.5) * p60
            for v65, v66 in v_u_12:key_itr() do
                if v66.IsLoaded == true then
                    if v65 == v_u_11 and v_u_17 ~= true then
                        if v66.Playing == false then
                            v66.Playing = true
                        end;
                        if v61 then
                            v66.Volume = v_u_3:clamp(v66.Volume - v64, 0, 0.125)
                        elseif v66.Volume < 0.125 then
                            v66.Volume = v_u_3:clamp(v66.Volume + v64, 0, 0.125)
                        end;
                    elseif v66.Playing then
                        if v66.Volume > 0 then
                            v66.Volume = v_u_3:clamp(v66.Volume - v64, 0, 0.125)
                        end;
                        if v66.Volume <= 0 then
                            v66.Playing = false
                        end;
                    end;
                end;
            end;
            local v67 = 0.125 * (v_u_21 / v_u_20)
            if v_u_17 == true then
                if v_u_16.IsLoaded == true then
                    if v61 then
                        v_u_16.Volume = v_u_3:clamp(v_u_16.Volume - v64, 0, v67)
                    elseif v_u_16.Volume < v67 then
                        v_u_16.Volume = v_u_3:clamp(v_u_16.Volume + v64, 0, v67)
                    end;
                end;
                p59:sync_club_bgm_state()
                v_u_16.Playing = true
            elseif v_u_16.Playing then
                if v_u_16.Volume > 0 then
                    v_u_16.Volume = v_u_3:clamp(v_u_16.Volume - v64, 0, v67)
                end;
                if v_u_16.Volume <= 0 then
                    v_u_16.Playing = false
                end;
            end;
        end;
        v_u_10.get_debug_string = function(p68) --[[ Name: get_debug_string ]] --[[ Line: 375 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_37, (copy 3): v_u_36, (ref 4): v_u_14 ]]
            return string.format("BGMManager _preview_assetid(%s) _preview_volume(%.2f) stack(%d) top[%d] _PreviewSound{Playing(%s) SoundId(%s) TimePosition(%.2f) TimeLength(%.2f) Volume(%.2f)}", tostring(v_u_13), v_u_37, v_u_36:count(), p68:get_preview_songkey(), tostring(v_u_14.Playing), tostring(v_u_14.SoundId), v_u_14.TimePosition, v_u_14.TimeLength, v_u_14.Volume);
        end;
        f_cons()
        return v_u_10;
    end
};
