-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:40 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_10 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_12 = require(game.ReplicatedStorage.Shared.Mission.MissionActiveData)
return {
    ["new"] = function(_, p_u_13, p_u_14, p_u_15, p_u_16, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_11, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_8, (copy 8): v_u_9, (copy 9): v_u_6, (copy 10): v_u_12, (copy 11): v_u_10, (copy 12): v_u_7 ]]
        local v_u_20 = v_u_3:new(p_u_14, p_u_15)
        local v_u_21 = nil
        local v_u_22 = 1
        local v_u_23 = 1
        local v_u_24 = v_u_2:new()
        local v_u_25 = nil
        local v_u_26 = 0
        local v_u_27 = 0
        local v_u_28 = nil
        local v_u_29 = 0
        local v_u_30 = 0
        local function f_cons() --[[ Name: cons ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_11, (copy 4): v_u_20, (copy 5): p_u_13, (ref 6): v_u_5, (ref 7): v_u_4, (copy 8): p_u_14, (ref 9): v_u_8, (copy 10): p_u_15, (ref 11): v_u_25, (ref 12): v_u_28, (copy 13): v_u_24, (ref 14): v_u_9, (copy 15): p_u_16, (copy 16): p_u_18, (copy 17): p_u_17, (ref 18): v_u_6, (ref 19): v_u_12, (copy 20): p_u_19, (ref 21): v_u_10 ]]
            v_u_21 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.MissionCompleteUI:Clone()
            v_u_21.Name = v_u_1:gen_name(v_u_21.Name)
            v_u_21.Parent = v_u_11:get_world_ui_folder()
            v_u_20._native_size = v_u_21.PrimaryPart.Size
            v_u_20._size = v_u_20._native_size
            v_u_20:layout()
            v_u_20:add_cycle_element(p_u_13, 1, v_u_5:new(v_u_4:new(v_u_20, v_u_21.PrimaryPart, v_u_21.BackButtonSurface), p_u_14, function() --[[ Line: 51 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_8, (ref 3): p_u_15, (ref 4): v_u_20 ]]
                p_u_13._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
                p_u_15:remove_menu(v_u_20)
            end))
            v_u_25 = v_u_4:new(v_u_20, v_u_21.PrimaryPart, v_u_21.TitleSurface)
            v_u_28 = v_u_4:new(v_u_20, v_u_21.PrimaryPart, v_u_21.ShineSurface)
            v_u_24:push_back(v_u_4:new(v_u_20, v_u_21.PrimaryPart, v_u_21.UISurface))
            v_u_24:push_back(v_u_25)
            v_u_24:push_back(v_u_28)
            local l_Frame_0 = v_u_21.UISurface.SurfaceGui.Frame
            local v31 = v_u_9:missiondata_get_mission_of_id_and_timeframe(p_u_16, p_u_18, p_u_17)
            if v31 == nil then
                return p_u_15:remove_menu(v_u_20);
            end;
            local l_AlbumArt_0 = l_Frame_0.MissionInfoSection.CoverSection.AlbumArt
            local l_AlbumArtOverlay_0 = l_Frame_0.MissionInfoSection.CoverSection.AlbumArtOverlay
            if v_u_9:mission_is_any_song(v31) then
                v_u_9:render_placeholder_cover_art(v31, l_AlbumArt_0, l_AlbumArtOverlay_0)
            else
                v_u_6:singleton():render_coverimage_for_key(l_AlbumArt_0, l_AlbumArtOverlay_0, v_u_9:mission_get_targetsong(v31))
            end;
            l_Frame_0.MissionInfoSection.Description.Text = v_u_9:get_mission_description_text(v31)
            v_u_9:render_difficulty_image(l_Frame_0.MissionInfoSection.DifficultySection.DifficultyIcon, v_u_9:mission_get_difficulty(v31))
            local v32 = p_u_13._player_blob_manager:get_player_blob()
            local v33 = v_u_12.MissionData:from_table(v31)
            l_Frame_0.MissionInfoSection.RewardSection.CurrencyIcon.Image = v33:get_reward_image()
            l_Frame_0.MissionInfoSection.RewardSection.CurrencyDisplay.Text = tostring(v33:get_reward_display_amount_for_playerblob_and_timeframe(v32, p_u_18))
            local v34 = false
            if p_u_19.DidPlayerBlobUpgradeDifficulty == true then
                l_Frame_0.RankUpgradeSection.Description.Text = "You\'ve reached rank:"
                v_u_9:render_difficulty_image(l_Frame_0.RankUpgradeSection.DifficultyIcon, v_u_9:playerblob_get_mission_difficulty(v32))
                p_u_13._sfx_manager:play_sfx(v_u_8.SFX_FANFARE)
                v34 = true
            elseif typeof(p_u_19.RemainingMissionsToRankUpgrade) == "number" and (p_u_19.RemainingMissionsToRankUpgrade > 0 and v_u_10:is_max_difficulty(v_u_9:playerblob_get_mission_difficulty(v32)) == false) then
                l_Frame_0.RankUpgradeSection.Description.Text = string.format("Complete %d more %s mission(s) to reach rank:", p_u_19.RemainingMissionsToRankUpgrade, v_u_10:difficulty_to_string(v_u_9:playerblob_get_mission_difficulty(v32)))
                v_u_9:render_difficulty_image(l_Frame_0.RankUpgradeSection.DifficultyIcon, v_u_10:difficulty_upgrade(v_u_9:playerblob_get_mission_difficulty(v32)))
            else
                l_Frame_0.RankUpgradeSection.Visible = false
            end;
            if v34 == false then
                p_u_13._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
            end;
        end;
        v_u_20.behaviour_update = function(p35, p36, _) --[[ Name: behaviour_update ]] --[[ Line: 118 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_26, (ref 3): v_u_7, (ref 4): v_u_27, (ref 5): v_u_25, (ref 6): v_u_30, (ref 7): v_u_29, (ref 8): v_u_28 ]]
            p35:behaviour_update_base(p36, p_u_13)
            v_u_26 = v_u_7:incr_wrap(v_u_26, v_u_7:sec_to_tick(1.23) * p36, 1)
            v_u_27 = v_u_7:incr_wrap(v_u_27, v_u_7:sec_to_tick(1.02) * p36, 1)
            v_u_25:set_scale(math.sin(v_u_26 * 3.141592653589793 * 2) * 0.1 + 1)
            v_u_25:set_rotation_z(math.sin(v_u_27 * 3.141592653589793 * 2) * 5)
            v_u_30 = v_u_7:incr_wrap(v_u_30, v_u_7:sec_to_tick(2.12) * p36, 1)
            v_u_29 = v_u_7:incr_wrap(v_u_29, v_u_7:sec_to_tick(20) * p36, 1)
            v_u_28:set_scale(math.sin(v_u_30 * 3.141592653589793 * 2) * 0.05 + 1)
            v_u_28:set_rotation_z(v_u_29 * 360)
        end;
        v_u_20.layout = function(p37) --[[ Name: layout ]] --[[ Line: 133 ]]
            --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_23, (ref 3): v_u_21, (copy 4): v_u_24 ]]
            p_u_14:uiobj_rescale_to_max_nxy(p37, 0.9, 0.8, v_u_23)
            v_u_21:SetPrimaryPartCFrame(p_u_14:get_cframe({
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p37:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            }))
            for v38 = 1, v_u_24:count() do
                v_u_24:get(v38):layout()
            end;
        end;
        v_u_20.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 146 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21:Destroy()
        end;
        v_u_20.set_alpha = function(_, p39) --[[ Name: set_alpha ]] --[[ Line: 150 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_1, (ref 3): v_u_21 ]]
            if v_u_22 ~= p39 then
                v_u_22 = p39
                v_u_1:r_set_alpha(v_u_21, v_u_22)
            end;
        end;
        v_u_20.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 156 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        v_u_20.set_scale = function(_, p40) --[[ Name: set_scale ]] --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23 = p40
        end;
        v_u_20.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 158 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23;
        end;
        v_u_20.get_native_size = function(p41) --[[ Name: get_native_size ]] --[[ Line: 160 ]]
            return p41._native_size;
        end;
        v_u_20.get_size = function(p42) --[[ Name: get_size ]] --[[ Line: 163 ]]
            return p42._size;
        end;
        v_u_20.set_size = function(p43, p44) --[[ Name: set_size ]] --[[ Line: 166 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            p43._size = p44
            v_u_21.PrimaryPart.Size = Vector3.new(p44.X, p44.Y, 0)
        end;
        v_u_20.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 170 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21.PrimaryPart.Position;
        end;
        v_u_20.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 173 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21.PrimaryPart.SurfaceGui;
        end;
        f_cons()
        return v_u_20;
    end
};
