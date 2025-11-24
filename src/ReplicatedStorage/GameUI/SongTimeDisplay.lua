-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:30 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.ChainCombo)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.FlashEvery)
local v_u_3 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_4 = require(game.ReplicatedStorage.Lobby.UI.ScrollingElementDisplay)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
return {
    ["new"] = function(_, p_u_7) --[[ Name: new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_3, (copy 4): v_u_4, (copy 5): v_u_5, (copy 6): v_u_6 ]]
        local v_u_8 = v_u_2:SPUIObjectBase()
        local v_u_9 = nil
        local v_u_10 = nil
        local v_u_11 = nil
        v_u_8.get_native_size = function(_) --[[ Name: get_native_size ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10;
        end;
        v_u_8.get_size = function(_) --[[ Name: get_size ]] --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11;
        end;
        v_u_8.set_size = function(_, p12) --[[ Name: set_size ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9 ]]
            v_u_11 = p12
            v_u_9.PrimaryPart.Size = Vector3.new(p12.X, p12.Y, 0)
        end;
        local v_u_13 = nil
        local v_u_14 = nil
        local function f_update_song_time_display() --[[ Name: update_song_time_display ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_1, (copy 3): p_u_7 ]]
            v_u_14.Text = string.format("%s / %s", v_u_1:format_ms_time(p_u_7:es_gamelocal_get_audiomanager():get_current_time_ms()), v_u_1:format_ms_time(p_u_7:es_gamelocal_get_audiomanager():get_song_length_ms()))
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_3, (ref 3): v_u_10, (ref 4): v_u_11, (copy 5): p_u_7, (ref 6): v_u_13, (ref 7): v_u_4, (ref 8): v_u_5, (ref 9): v_u_14, (copy 10): f_update_song_time_display, (copy 11): v_u_8 ]]
            v_u_9 = game.ReplicatedStorage.WorldUIProto.SongTimeDisplay:Clone()
            v_u_9.Parent = v_u_3:get_world_ui_folder()
            v_u_10 = v_u_9.PrimaryPart.Size
            v_u_11 = v_u_10
            local v15 = p_u_7:es_gamelocal_get_audiomanager():get_song_key()
            local l_Frame_0 = v_u_9.PrimaryPart.SurfaceGui.Frame
            v_u_13 = v_u_4:new(l_Frame_0.ScrollingFrame.ScrollText1, l_Frame_0.ScrollingFrame.ScrollText2)
            v_u_13:set_text(string.format("%s - Artist: %s - ", v_u_5:singleton():get_title_for_key(v15), v_u_5:singleton():get_artist_for_key(v15)))
            v_u_14 = l_Frame_0.TimeDisplay
            f_update_song_time_display()
            v_u_8:layout()
        end;
        v_u_8.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            v_u_9:Destroy()
            v_u_9 = nil
        end;
        local v_u_16 = v_u_2:cframe_params_default()
        v_u_16.PositionNXY:set(1, 0)
        local l__spui_0 = p_u_7._spui
        v_u_8.layout = function(p17) --[[ Name: layout ]] --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): l__spui_0, (copy 3): v_u_16, (copy 4): f_update_song_time_display ]]
            if v_u_9 ~= nil then
                p17:opt_rescale_to_max_nxy(l__spui_0, 0.4, 0.3)
                v_u_16.OffsetXYZ:from_vector3(p17:anchored_offset(1, 0) + Vector3.new(-p17:get_size().X * 0.01, -p17:get_size().Y * 0.1))
                local v18, v19 = p17:opt_update_cframe_params(l__spui_0, v_u_16)
                if v18 == true then
                    v_u_9:SetPrimaryPartCFrame(v19)
                end;
                f_update_song_time_display()
            end;
        end;
        local l_GameSongMarker_0 = v_u_6.Test.GameSongMarker
        v_u_6:register_ui_needs_refresh_should_run_test_type(l_GameSongMarker_0)
        v_u_8.update = function(p20, _, _) --[[ Name: update ]] --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): l_GameSongMarker_0, (ref 3): v_u_9, (ref 4): v_u_13 ]]
            local v21 = v_u_6:singleton()
            if v21:should_run(l_GameSongMarker_0) == false then
                return;
            else
                local v22 = v21:get_test_state(l_GameSongMarker_0):get_dt_scale()
                if v_u_9 ~= nil then
                    p20:layout()
                    v_u_13:update(v22)
                end;
            end;
        end;
        f_cons()
        return v_u_8;
    end
};
