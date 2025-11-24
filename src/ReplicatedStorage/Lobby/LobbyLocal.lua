-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:31 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Local.ObjectPool)
require(game.ReplicatedStorage.Effects.EffectSystem)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.Lobby.LobbyUIManager)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.Local.GameJoinProtocol)
require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.LocalShared.ShopLocalProtocol)
local v_u_10 = require(game.ReplicatedStorage.LocalShared.BGMManager)
local v_u_11 = require(game.ReplicatedStorage.Lobby.LobbyNPCManager)
local v_u_12 = require(game.ReplicatedStorage.Lobby.LobbyEnvManager)
local s_UserInputService_0 = game:GetService("UserInputService")
require(game.ReplicatedStorage.Avatar.SPAvatarUtil)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_13 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_14 = require(game.ReplicatedStorage.LocalShared.TradeLocalProtocol)
local v_u_15 = require(game.ReplicatedStorage.Lobby.LobbySpectateManager)
local v_u_16 = require(game.ReplicatedStorage.LocalShared.IntersectZoneManager)
local v_u_17 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_19 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_20 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_21 = require(game.ReplicatedStorage.Shared.HUDNotification)
local v22 = require(game.ReplicatedStorage.Lobby.Util.LobbyLocalMode)
local v_u_23 = require(game.ReplicatedStorage.Shared.NoCollideGroup)
local v_u_24 = require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v25 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_26 = nil
local v_u_27 = nil
local v_u_28 = nil
local v_u_29 = nil
local v_u_30 = nil
v25:require_client(function() --[[ Line: 43 ]]
    --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_27, (ref 3): v_u_28, (ref 4): v_u_29, (ref 5): v_u_30 ]]
    v_u_26 = require(game.ReplicatedStorage.Lobby.Menus.ArtistEventUI)
    v_u_27 = require(game.ReplicatedStorage.Lobby.UI.ArtistEventUI.ArtistEventUITab_Leaderboard)
    v_u_28 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
    v_u_29 = require(game.ReplicatedStorage.Lobby.UI.MatchMakingV3GameStageSelectSection)
    v_u_30 = require(game.ReplicatedStorage.Lobby.EventIntegration.LobbyEventIntegrationManager)
end)
local v_u_31 = {
    ["Mode"] = v22
}
local v_u_32 = false
local v_u_33 = CFrame.new()
v_u_31.new = function(_, p_u_34, _) --[[ Name: new ]] --[[ Line: 57 ]]
    --[[ Upvalues: (copy 1): v_u_31, (copy 2): v_u_14, (copy 3): v_u_7, (copy 4): v_u_9, (copy 5): v_u_11, (copy 6): v_u_12, (copy 7): v_u_15, (ref 8): v_u_30, (copy 9): v_u_4, (copy 10): v_u_13, (copy 11): v_u_1, (copy 12): v_u_2, (copy 13): s_UserInputService_0, (copy 14): v_u_8, (copy 15): v_u_10, (copy 16): v_u_24, (copy 17): v_u_6, (copy 18): v_u_21, (ref 19): v_u_26, (ref 20): v_u_27, (copy 21): v_u_23, (ref 22): v_u_32, (ref 23): v_u_33, (copy 24): v_u_18, (copy 25): v_u_19, (copy 26): v_u_5, (copy 27): v_u_16, (copy 28): v_u_17, (copy 29): v_u_3, (copy 30): v_u_20, (ref 31): v_u_28, (ref 32): v_u_29 ]]
    local v_u_35 = p_u_34:local_services_copy()
    v_u_35._current_mode = v_u_31.Mode.Loading
    v_u_35._trade_local_protocol = v_u_14:new(p_u_34._evt)
    v_u_35._ui_manager = v_u_7:new(v_u_35, p_u_34)
    v_u_35._game_join_protocol = v_u_9:new(p_u_34)
    v_u_35._npcs = v_u_11:new(v_u_35, p_u_34)
    v_u_35._env = v_u_12:new(v_u_35)
    v_u_35._spectate_manager = v_u_15:new(p_u_34)
    v_u_35._event_integration_manager = v_u_30:new(p_u_34, v_u_35)
    local v_u_36 = v_u_4:new()
    v_u_35.register_lobby_update_fn = function(_, p37) --[[ Name: register_lobby_update_fn ]] --[[ Line: 73 ]]
        --[[ Upvalues: (copy 1): v_u_36 ]]
        v_u_36:push_back(p37)
    end;
    local v_u_38 = v_u_4:new()
    v_u_35.register_lobby_exit_fn = function(_, p39) --[[ Name: register_lobby_exit_fn ]] --[[ Line: 76 ]]
        --[[ Upvalues: (copy 1): v_u_38 ]]
        v_u_38:push_back(p39)
    end;
    v_u_35.get_control_script = function(p40) --[[ Name: get_control_script ]] --[[ Line: 78 ]]
        return p40._control_script;
    end;
    v_u_35.get_camera_script = function(p41) --[[ Name: get_camera_script ]] --[[ Line: 79 ]]
        return p41._camera_script;
    end;
    v_u_35.get_animate_script = function(p42) --[[ Name: get_animate_script ]] --[[ Line: 80 ]]
        return p42._animate_script;
    end;
    v_u_35.get_current_dayid = function(_) --[[ Name: get_current_dayid ]] --[[ Line: 82 ]]
        --[[ Upvalues: (copy 1): v_u_35 ]]
        return v_u_35._player_blob_manager:get_day_id();
    end;
    local v_u_43 = v_u_4:new()
    local v_u_44 = nil
    v_u_35.get_local_character = function(_) --[[ Name: get_local_character ]] --[[ Line: 86 ]]
        --[[ Upvalues: (ref 1): v_u_44 ]]
        return v_u_44;
    end;
    local v_u_45 = {
        ["EnvironmentSetup"] = v_u_13,
        ["SPUtil"] = v_u_1
    }
    local v_u_46 = {
        ["CurveUtil"] = v_u_2
    }
    local v_u_47 = {
        ["CurveUtil"] = v_u_2
    }
    local function _() --[[ Name: cons ]] --[[ Line: 100 ]]
        --[[ Upvalues: (copy 1): v_u_35, (ref 2): v_u_31 ]]
        v_u_35._current_mode = v_u_31.Mode.PreStart
    end;
    v_u_35.get_current_mode = function(p48) --[[ Name: get_current_mode ]] --[[ Line: 104 ]]
        return p48._current_mode;
    end;
    v_u_35.enqueue_loaded_callback = function(p49, p50) --[[ Name: enqueue_loaded_callback ]] --[[ Line: 106 ]]
        --[[ Upvalues: (ref 1): v_u_31, (copy 2): v_u_43 ]]
        if p49._current_mode == v_u_31.Mode.Game then
            p50(p49)
        else
            v_u_43:push_back(p50)
        end;
    end;
    local function _(p_u_51) --[[ Name: set_control_scripts_enabled ]] --[[ Line: 114 ]]
        --[[ Upvalues: (copy 1): v_u_35, (ref 2): s_UserInputService_0, (ref 3): v_u_8 ]]
        local v52, v53 = pcall(function() --[[ Line: 115 ]]
            --[[ Upvalues: (ref 1): v_u_35, (copy 2): p_u_51, (ref 3): s_UserInputService_0 ]]
            v_u_35._control_script:set_enabled(p_u_51)
            v_u_35._camera_script:set_enabled(p_u_51)
            s_UserInputService_0.ModalEnabled = not p_u_51
        end)
        if not v52 then
            v_u_8:warnf("set_control_scripts_enabled error(%s)", v53)
        end;
    end;
    v_u_35.start_lobby = function(p_u_54) --[[ Name: start_lobby ]] --[[ Line: 125 ]]
        --[[ Upvalues: (copy 1): v_u_35, (ref 2): v_u_31, (ref 3): v_u_8, (ref 4): v_u_10, (ref 5): v_u_24, (copy 6): v_u_35, (ref 7): s_UserInputService_0, (copy 8): v_u_45, (copy 9): v_u_46, (copy 10): v_u_43 ]]
        if v_u_35._current_mode ~= v_u_31.Mode.PreStart then
            v_u_8:errf("LobbyLocal:start_lobby() mode(%d)", v_u_35._current_mode)
        end;
        v_u_35._current_mode = v_u_31.Mode.Loading
        v_u_35._bgm_manager:play_bgm(v_u_10.BGM_LOBBY)
        v_u_24:sync_characters_to_cframe()
        v_u_8:puts("LobbyLocal:start_lobby -> request_spawn_character")
        p_u_54:request_spawn_character(function() --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_35, (ref 3): s_UserInputService_0, (ref 4): v_u_8, (copy 5): p_u_54, (ref 6): v_u_45, (ref 7): v_u_46, (ref 8): v_u_31, (ref 9): v_u_43 ]]
            v_u_35._dance_club_manager:request_current_song_info()
            v_u_35._ui_manager:initialize_ui(v_u_35)
            v_u_35._npcs:initialize_npcs()
            local v61, v62 = pcall(function() --[[ Line: 141 ]]
                --[[ Upvalues: (ref 1): v_u_35, (ref 2): s_UserInputService_0, (ref 3): v_u_8, (ref 4): p_u_54, (ref 5): v_u_45, (ref 6): v_u_46 ]]
                local v_u_55 = true
                local v56, v57 = pcall(function() --[[ Line: 115 ]]
                    --[[ Upvalues: (ref 1): v_u_35, (copy 2): v_u_55, (ref 3): s_UserInputService_0 ]]
                    v_u_35._control_script:set_enabled(v_u_55)
                    v_u_35._camera_script:set_enabled(v_u_55)
                    s_UserInputService_0.ModalEnabled = not v_u_55
                end)
                if not v56 then
                    v_u_8:warnf("set_control_scripts_enabled error(%s)", v57)
                end;
                p_u_54._camera_script:update(0, v_u_45)
                p_u_54._control_script:update(0, v_u_46)
                local v_u_58 = false
                local v59, v60 = pcall(function() --[[ Line: 115 ]]
                    --[[ Upvalues: (ref 1): v_u_35, (copy 2): v_u_58, (ref 3): s_UserInputService_0 ]]
                    v_u_35._control_script:set_enabled(v_u_58)
                    v_u_35._camera_script:set_enabled(v_u_58)
                    s_UserInputService_0.ModalEnabled = not v_u_58
                end)
                if not v59 then
                    v_u_8:warnf("set_control_scripts_enabled error(%s)", v60)
                end;
            end)
            if not v61 then
                v_u_8:warnf("start_lobby control_scripts err(%s)", v62)
            end;
            v_u_35._current_mode = v_u_31.Mode.Game
            for v63 = 1, v_u_43:count() do
                v_u_43:get(v63)(p_u_54)
            end;
            v_u_43:clear()
            local v64 = v_u_35._lobby_join:get_registered_lobby_join_start_fns()
            if v64:count() > 0 then
                for _, v65 in v64:key_itr() do
                    v65(v_u_35)
                end;
            end;
        end)
    end;
    v_u_35.cache_character_cframe = function(_) --[[ Name: cache_character_cframe ]] --[[ Line: 170 ]]
        --[[ Upvalues: (ref 1): v_u_44, (copy 2): v_u_35 ]]
        if v_u_44 == nil then
            return;
        else
            local v66 = v_u_44:FindFirstChild("Humanoid")
            if v66 == nil then
                return;
            elseif v66.RootPart ~= nil then
                v_u_35._lobby_join:set_cached_character_cframe(v66.RootPart.CFrame)
            end;
        end;
    end;
    local v_u_67 = -1
    v_u_35.get_character_group_id = function(_) --[[ Name: get_character_group_id ]] --[[ Line: 179 ]]
        --[[ Upvalues: (ref 1): v_u_67 ]]
        return v_u_67;
    end;
    local v_u_68 = -1
    v_u_35.get_transparent_group_id = function(_) --[[ Name: get_transparent_group_id ]] --[[ Line: 182 ]]
        --[[ Upvalues: (ref 1): v_u_68 ]]
        return v_u_68;
    end;
    v_u_35.request_spawn_character = function(p_u_69, p_u_70) --[[ Name: request_spawn_character ]] --[[ Line: 184 ]]
        --[[ Upvalues: (copy 1): v_u_35, (ref 2): v_u_6, (ref 3): v_u_8, (ref 4): v_u_1, (ref 5): v_u_67, (ref 6): v_u_68, (ref 7): v_u_21, (ref 8): v_u_26, (ref 9): v_u_27, (ref 10): v_u_13, (ref 11): v_u_23 ]]
        v_u_35._evt:clear_pending_on(v_u_6.EVT_Lobby_ServerAcknowledgeClientEnter)
        v_u_35._evt:wait_on_event_once(v_u_6.EVT_Lobby_ServerAcknowledgeClientEnter, function(p71) --[[ Line: 186 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_1, (ref 3): v_u_67, (ref 4): v_u_68, (ref 5): v_u_21, (ref 6): v_u_26, (ref 7): v_u_27, (ref 8): v_u_13, (ref 9): v_u_23, (ref 10): v_u_35, (copy 11): p_u_69, (copy 12): p_u_70 ]]
            v_u_8:puts("EVT_Lobby_ServerAcknowledgeClientEnter %s", v_u_1:table_to_string(p71))
            v_u_67 = p71.CharacterGroupID
            v_u_68 = p71.TransparentGroupID
            local v72 = v_u_21:table_to_list(p71.HUDNotifications)
            for v73 = 1, v72:count() do
                local v74 = v72:get(v73)
                if v74:get_type() == v_u_21.Type.ArtistEventButton then
                    v_u_26:set_notification_display(true, v74:get_count())
                    v_u_27:set_notification_display(true, v74:get_count())
                end;
            end;
            local v75 = v_u_13:get_gear_shop_model_humanoids()
            for v76 = 1, v75:count() do
                local v77 = v75:get(v76)
                if v77.Parent then
                    v_u_23:apply_group_id(v77.Parent, v_u_35:get_transparent_group_id())
                end;
            end;
            p_u_69:cons_on_character_created(p_u_70)
        end)
        v_u_35._evt:fire_event_to_server(v_u_6.EVT_Lobby_ClientNotifyEnter, v_u_35._lobby_join:has_cached_character_cframe(), v_u_35._lobby_join:get_cached_character_cframe())
    end;
    local function f_cleanup_character_scripts() --[[ Name: cleanup_character_scripts ]] --[[ Line: 218 ]]
        --[[ Upvalues: (copy 1): v_u_35, (ref 2): v_u_1 ]]
        if v_u_35._control_script ~= nil then
            v_u_35._control_script:destroy(v_u_1)
            v_u_35._control_script = nil
        end;
        if v_u_35._camera_script ~= nil then
            v_u_35._camera_script:destroy(v_u_1)
            v_u_35._camera_script = nil
        end;
        if v_u_35._animate_script ~= nil then
            v_u_35._animate_script:destroy(v_u_1)
            v_u_35._animate_script = nil
        end;
        if v_u_35._sound_script ~= nil then
            v_u_35._sound_script:destroy(v_u_1)
            v_u_35._sound_script = nil
        end;
    end;
    v_u_35.cons_on_character_created = function(p_u_78, p_u_79) --[[ Name: cons_on_character_created ]] --[[ Line: 237 ]]
        --[[ Upvalues: (ref 1): v_u_44, (ref 2): v_u_8, (ref 3): v_u_13, (copy 4): f_cleanup_character_scripts, (copy 5): v_u_35, (ref 6): v_u_1, (ref 7): v_u_32, (ref 8): v_u_33, (copy 9): v_u_35, (ref 10): s_UserInputService_0, (copy 11): p_u_34 ]]
        v_u_44 = game.Players.LocalPlayer.Character
        if v_u_44 == nil then
            v_u_8:errf("LobbyLocal:cons_on_character_created LocalPlayer Character is nil")
        end;
        v_u_13:move_to_local_character_folder(v_u_44)
        local v80 = v_u_44:FindFirstChild("Humanoid")
        if v80 then
            v80.Died:connect(function() --[[ Line: 245 ]]
                --[[ Upvalues: (ref 1): f_cleanup_character_scripts, (ref 2): v_u_35, (copy 3): p_u_78 ]]
                f_cleanup_character_scripts()
                v_u_35._lobby_join:reset_cached_character_cframe()
                p_u_78:request_spawn_character()
            end)
        end;
        spawn(function() --[[ Line: 253 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_8, (ref 3): v_u_44, (copy 4): p_u_78, (ref 5): v_u_32, (ref 6): v_u_33, (ref 7): v_u_35, (ref 8): s_UserInputService_0, (copy 9): p_u_79, (ref 10): p_u_34 ]]
            if v_u_1:is_dev_build() then
                v_u_8:puts("LobbyLocal:cons_on_character_created() DefaultAnimateScript")
            end;
            local v81 = game.ReplicatedStorage.Lobby.DefaultAnimateScript:Clone()
            v81.Parent = v_u_44
            p_u_78._animate_script = v81.Self:Invoke()
            if v_u_1:is_dev_build() then
                v_u_8:puts("LobbyLocal:cons_on_character_created() DefaultSoundScript")
            end;
            local v82 = game.ReplicatedStorage.Lobby.DefaultSoundScript:Clone()
            v82.Parent = v_u_44
            p_u_78._sound_script = v82.Self:Invoke()
            if v_u_1:is_dev_build() then
                v_u_8:puts("LobbyLocal:cons_on_character_created() DefaultControlScript")
            end;
            local v83 = game.ReplicatedStorage.Lobby.DefaultControlScript:Clone()
            v83.Parent = game.Players.LocalPlayer.PlayerScripts
            p_u_78._control_script = v83.Self:Invoke()
            local v84 = v_u_1:get_camera()
            if v_u_1:is_dev_build() then
                v_u_8:puts("LobbyLocal:cons_on_character_created() DefaultCameraScript")
            end;
            local v85 = game.ReplicatedStorage.Lobby.DefaultCameraScript:Clone()
            v85.Parent = game.Players.LocalPlayer.PlayerScripts
            p_u_78._camera_script = v85.Self:Invoke()
            p_u_78._camera_script:connect_to_localplayer()
            v84.CameraType = Enum.CameraType.Custom
            v84.CameraSubject = game.Players.LocalPlayer.Character.Humanoid
            if v_u_32 then
                v84.CFrame = v_u_33
            else
                p_u_78._camera_script:set_look_behind_character(v_u_33)
            end;
            if v_u_1:is_dev_build() then
                v_u_8:puts("LobbyLocal:cons_on_character_created() scripts finished")
            end;
            local v_u_86 = false
            local v87, v88 = pcall(function() --[[ Line: 115 ]]
                --[[ Upvalues: (ref 1): v_u_35, (copy 2): v_u_86, (ref 3): s_UserInputService_0 ]]
                v_u_35._control_script:set_enabled(v_u_86)
                v_u_35._camera_script:set_enabled(v_u_86)
                s_UserInputService_0.ModalEnabled = not v_u_86
            end)
            if not v87 then
                v_u_8:warnf("set_control_scripts_enabled error(%s)", v88)
            end;
            if p_u_79 ~= nil then
                p_u_34._update_enqueue_fn:enqueue_function(function() --[[ Line: 301 ]]
                    --[[ Upvalues: (ref 1): p_u_78, (ref 2): p_u_79 ]]
                    p_u_78:cache_character_cframe()
                    p_u_79()
                end, 0)
            end;
        end)
    end;
    v_u_35.set_character_random_position_around_anchors_fn = function(p89, p_u_90) --[[ Name: set_character_random_position_around_anchors_fn ]] --[[ Line: 309 ]]
        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_1 ]]
        local v_u_91 = nil
        local v_u_92 = nil
        local v_u_93 = nil
        local v_u_94 = nil
        local v_u_95 = nil
        local v101, v102 = pcall(function() --[[ Line: 311 ]]
            --[[ Upvalues: (ref 1): v_u_91, (ref 2): v_u_92, (ref 3): v_u_93, (ref 4): v_u_94, (ref 5): v_u_95, (copy 6): p_u_90 ]]
            local v96, v97, v98, v99, v100 = p_u_90()
            v_u_91 = v96
            v_u_92 = v97
            v_u_93 = v98
            v_u_94 = v99
            v_u_95 = v100
            if v_u_91:IsA("BasePart") ~= true or v_u_92:IsA("BasePart") ~= true then
                error("anchor unexpected type")
            end;
        end)
        if not v101 then
            return v_u_8:warnf("set_character_random_position_around error(%s)", v102);
        end;
        local l_CFrame_0 = v_u_91.CFrame
        local l_magnitude_0 = (v_u_1:get_localplayer_cframe().p - l_CFrame_0.p).magnitude
        local l_Position_0 = v_u_92.CFrame.Position
        if l_magnitude_0 > 15 then
            p89:set_local_character_cframe(CFrame.new(v_u_1:get_randomized_character_position(l_CFrame_0.Position, l_Position_0, v_u_93, v_u_94, v_u_95), l_Position_0))
        end;
    end;
    v_u_35.transition_local_camera_to_anchors_fn = function(_, p_u_103) --[[ Name: transition_local_camera_to_anchors_fn ]] --[[ Line: 345 ]]
        --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_35 ]]
        local v_u_104 = nil
        local v_u_105 = nil
        local v108, v109 = pcall(function() --[[ Line: 347 ]]
            --[[ Upvalues: (ref 1): v_u_104, (ref 2): v_u_105, (copy 3): p_u_103 ]]
            local v106, v107 = p_u_103()
            v_u_104 = v106
            v_u_105 = v107
            if v_u_104:IsA("BasePart") ~= true or v_u_105:IsA("BasePart") ~= true then
                error("anchor unexpected type")
            end;
        end)
        if not v108 then
            return v_u_8:warnf("set_character_random_position_around error(%s)", v109);
        end;
        v_u_35:transition_local_camera_cframe(CFrame.new(v_u_104.CFrame.Position, v_u_105.CFrame.Position))
    end;
    local v_u_110 = false
    local v_u_111 = CFrame.new()
    v_u_35.set_local_character_cframe = function(_, p112) --[[ Name: set_local_character_cframe ]] --[[ Line: 364 ]]
        --[[ Upvalues: (copy 1): v_u_35, (ref 2): v_u_31, (ref 3): v_u_110, (ref 4): v_u_111 ]]
        if v_u_35._current_mode ~= v_u_31.Mode.Cleanup then
            v_u_110 = true
            v_u_111 = p112
        end;
    end;
    local v_u_113 = {
        ["Finished"] = 0,
        ["RotateToFacing"] = 1,
        ["MoveToTarget"] = 2,
        ["RotateToFinal"] = 3,
        ["NearTransformInterp"] = 4
    }
    local v_u_114 = CFrame.new()
    local v_u_115 = CFrame.new()
    local v_u_116 = 0
    local l_Finished_0 = v_u_113.Finished
    v_u_35.transition_local_camera_cframe = function(_, p117) --[[ Name: transition_local_camera_cframe ]] --[[ Line: 382 ]]
        --[[ Upvalues: (copy 1): v_u_35, (ref 2): v_u_31, (ref 3): v_u_114, (ref 4): v_u_115, (ref 5): v_u_1, (ref 6): v_u_116, (ref 7): l_Finished_0, (copy 8): v_u_113 ]]
        if v_u_35._current_mode == v_u_31.Mode.Cleanup then
            return;
        elseif v_u_35._current_mode == v_u_31.Mode.Loading then
            return;
        else
            v_u_114 = p117
            v_u_115 = v_u_1:get_camera().CFrame
            v_u_1:get_camera().Focus = v_u_1:get_camera().CFrame
            v_u_116 = 0
            if v_u_1:cframe_delta(v_u_114, v_u_115) < 0.1 then
                l_Finished_0 = v_u_113.Finished
                v_u_116 = 1
                return;
            elseif (v_u_114.p - v_u_115.p).magnitude < 60 then
                l_Finished_0 = v_u_113.NearTransformInterp
            else
                l_Finished_0 = v_u_113.RotateToFacing
            end;
        end;
    end;
    v_u_35.transition_local_camera_cframe_finished = function(_) --[[ Name: transition_local_camera_cframe_finished ]] --[[ Line: 401 ]]
        --[[ Upvalues: (ref 1): l_Finished_0, (copy 2): v_u_113 ]]
        return l_Finished_0 == v_u_113.Finished;
    end;
    local function _(p118) --[[ Name: anim_t_for_transition_t ]] --[[ Line: 405 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        return v_u_2:BezierPt2ForT(0, 0, 1, 0, 0, 1, 1, 1, p118).Y;
    end;
    v_u_35.update_character_camera_transitions = function(_, p119) --[[ Name: update_character_camera_transitions ]] --[[ Line: 415 ]]
        --[[ Upvalues: (ref 1): v_u_110, (copy 2): v_u_35, (ref 3): v_u_111, (ref 4): l_Finished_0, (copy 5): v_u_113, (ref 6): v_u_115, (ref 7): v_u_1, (ref 8): v_u_114, (ref 9): v_u_116, (ref 10): v_u_2 ]]
        if v_u_110 == true then
            v_u_110 = false
            local v120 = v_u_35:get_local_character()
            if v120 ~= nil and v120.PrimaryPart ~= nil then
                v120:SetPrimaryPartCFrame(v_u_111)
            end;
        end;
        if l_Finished_0 == v_u_113.RotateToFacing then
            local v121 = v_u_115
            local v122 = v_u_1:lookat_matrix(v_u_115.p, v_u_114.p)
            v_u_116 = v_u_1:clamp(v_u_116 + p119 * v_u_2:sec_to_tick(v_u_1:cframe_interpolator(v121, v122) / 6), 0, 1)
            v_u_1:get_camera().CFrame = v121:lerp(v122, v_u_2:BezierPt2ForT(0, 0, 1, 0, 0, 1, 1, 1, v_u_116).Y)
            v_u_1:get_camera().Focus = v_u_1:get_camera().CFrame
            if v_u_116 >= 1 then
                v_u_116 = 0
                l_Finished_0 = v_u_113.MoveToTarget
                return;
            end;
        elseif l_Finished_0 == v_u_113.MoveToTarget then
            local v123 = v_u_1:lookat_matrix(v_u_115.p, v_u_114.p)
            local v124 = v123 - v123.p + v_u_114.p
            v_u_116 = v_u_1:clamp(v_u_116 + p119 * v_u_2:sec_to_tick((v124.p - v123.p).magnitude / 250), 0, 1)
            v_u_1:get_camera().CFrame = v123:lerp(v124, v_u_2:BezierPt2ForT(0, 0, 1, 0, 0, 1, 1, 1, v_u_116).Y)
            v_u_1:get_camera().Focus = v_u_1:get_camera().CFrame
            if v_u_116 >= 1 then
                v_u_116 = 0
                l_Finished_0 = v_u_113.RotateToFinal
                return;
            end;
        elseif l_Finished_0 == v_u_113.RotateToFinal then
            local v125 = v_u_1:lookat_matrix(v_u_115.p, v_u_114.p)
            local v126 = v125 - v125.p + v_u_114.p
            local v127 = v_u_114
            v_u_116 = v_u_1:clamp(v_u_116 + p119 * v_u_2:sec_to_tick(v_u_1:cframe_interpolator(v126, v127) / 6), 0, 1)
            v_u_1:get_camera().CFrame = v126:lerp(v127, v_u_2:BezierPt2ForT(0, 0, 1, 0, 0, 1, 1, 1, v_u_116).Y)
            v_u_1:get_camera().Focus = v_u_1:get_camera().CFrame
            if v_u_116 >= 1 then
                l_Finished_0 = v_u_113.Finished
                return;
            end;
        elseif l_Finished_0 == v_u_113.NearTransformInterp then
            v_u_116 = v_u_1:clamp(v_u_116 + p119 * v_u_2:sec_to_tick(0.5), 0, 1)
            v_u_1:get_camera().CFrame = v_u_115:lerp(v_u_114, v_u_2:BezierPt2ForT(0, 0, 1, 0, 0, 1, 1, 1, v_u_116).Y)
            v_u_1:get_camera().Focus = v_u_1:get_camera().CFrame
            if v_u_116 >= 1 then
                l_Finished_0 = v_u_113.Finished
            end;
        end;
    end;
    v_u_35.character_perform_danceid = function(_, p128) --[[ Name: character_perform_danceid ]] --[[ Line: 484 ]]
        --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_35 ]]
        local v_u_129 = v_u_18:singleton():get_dance_animation_for_id(p128)
        if v_u_129 then
            spawn(function() --[[ Line: 487 ]]
                --[[ Upvalues: (ref 1): v_u_35, (copy 2): v_u_129 ]]
                v_u_35._animate_script:play_animation_instance(v_u_129)
                v_u_35._follow_npc_manager:on_local_character_play_animation(v_u_129)
            end)
        end;
    end;
    local function f_play_animation_synced_to_name(p130, p131, p132) --[[ Name: play_animation_synced_to_name ]] --[[ Line: 494 ]]
        --[[ Upvalues: (copy 1): v_u_35, (ref 2): v_u_18, (ref 3): v_u_19 ]]
        if v_u_35._animate_script ~= nil then
            if v_u_35._animate_script:get_current_animation_instance() ~= p130 then
                local v133 = v_u_18:singleton():assetid_to_danceid(p130.AnimationId)
                if v_u_18:singleton():contains_dance_for_id(v133) then
                    v_u_35._chat:get_system_channel():add_message_to_channel(v_u_19:new(string.format("Dancing \"%s\" along with %s!", tostring((v_u_18:singleton():get_dance_name_for_id(v133))), p132)):set_icon(v_u_18:singleton():get_dance_icon_for_id(v133)))
                end;
            end;
            v_u_35._animate_script:play_animation_instance(p130, p131)
            v_u_35._follow_npc_manager:on_local_character_play_animation(p130, p131)
        end;
    end;
    v_u_35.is_control_pressed = function(p134) --[[ Name: is_control_pressed ]] --[[ Line: 512 ]]
        if p134._control_script == nil then
            return false;
        else
            return p134._control_script:get_move_vector().magnitude > 0 and true or p134._control_script:is_jumping();
        end;
    end;
    local v_u_135 = v_u_5:new():add_set_from_table_list({
        v_u_16.ZoneName.Club,
        v_u_16.ZoneName.CompeteTower,
        v_u_16.ZoneName.MusicShop,
        v_u_16.ZoneName.GuildBuilding,
        v_u_16.ZoneName.GearShop,
        v_u_16.ZoneName.Marketplace
    })
    v_u_35.update = function(p136, p137) --[[ Name: update ]] --[[ Line: 528 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_35, (ref 3): v_u_31, (ref 4): s_UserInputService_0, (copy 5): v_u_35, (ref 6): v_u_8, (copy 7): v_u_45, (copy 8): v_u_36, (copy 9): v_u_46, (copy 10): v_u_47, (copy 11): v_u_135, (ref 12): v_u_16, (ref 13): v_u_17, (ref 14): v_u_10, (ref 15): v_u_13, (ref 16): v_u_3, (ref 17): v_u_18, (copy 18): f_play_animation_synced_to_name, (ref 19): v_u_6, (copy 20): p_u_34 ]]
        v_u_1:profilebegin("LobbyLocal:update")
        v_u_35._event_integration_manager:update(p137)
        if v_u_35._current_mode ~= v_u_31.Mode.Loading and v_u_35._current_mode == v_u_31.Mode.Game then
            v_u_1:profilebegin("LobbyLocal:set_enabled")
            local v138 = p136._ui_manager:swallow_control_input()
            if v138 ~= s_UserInputService_0.ModalEnabled then
                local v_u_139 = not v138
                local v140, v141 = pcall(function() --[[ Line: 115 ]]
                    --[[ Upvalues: (ref 1): v_u_35, (copy 2): v_u_139, (ref 3): s_UserInputService_0 ]]
                    v_u_35._control_script:set_enabled(v_u_139)
                    v_u_35._camera_script:set_enabled(v_u_139)
                    s_UserInputService_0.ModalEnabled = not v_u_139
                end)
                if not v140 then
                    v_u_8:warnf("set_control_scripts_enabled error(%s)", v141)
                end;
            end;
            v_u_1:profileend()
            v_u_1:profilebegin("LobbyLocal:camera_script_update")
            if p136._camera_script then
                p136._camera_script:update(p137, v_u_45)
            end;
            v_u_1:profileend()
            local v142 = v_u_35._lobby_join:get_registered_lobby_join_update_fns()
            if v142:count() > 0 then
                for _, v143 in v142:key_itr() do
                    v143(p137, v_u_35)
                end;
            end;
            if v_u_36:count() > 0 then
                for _, v144 in v_u_36:key_itr() do
                    v144(p137, v_u_35)
                end;
            end;
            v_u_1:profilebegin("LobbyLocal:control_script_update")
            if p136._control_script then
                p136._control_script:update(p137, v_u_46)
            end;
            v_u_1:profileend()
            if p136:is_control_pressed() and p136._animate_script ~= nil then
                p136._animate_script:control_pressed()
            end;
            if p136._sound_script ~= nil then
                p136._sound_script:update(p137, v_u_47)
            end;
            p136:update_character_camera_transitions(p137)
            v_u_1:update()
            v_u_1:profilebegin("LobbyLocal:bgm_calc")
            local _, v145 = v_u_1:get_local_character_humanoid_rootpart()
            if v145 then
                local v146 = v_u_35._intersect_zone_manager:get_intersecting_zones_for_point(v145.Position, v_u_135)
                local v147 = true
                local v148 = v146:contains(v_u_16.ZoneName.Club)
                local v149 = v148 or v_u_35._player_settings_manager:get_key(v_u_17.Key.RadioEnabled)
                if (v_u_35._bgm_manager:get_playing_bgm_key() == v_u_10.BGM_LOBBY or (v_u_35._bgm_manager:get_playing_bgm_key() == v_u_10.BGM_SHOP or v_u_35._bgm_manager:get_playing_bgm_key() == v_u_10.BGM_MATCHMAKING)) and (v149 or p136._ui_manager:handles_bgm() ~= true) then
                    local v150 = false
                    local v151 = false
                    if v149 then
                        v_u_35._bgm_manager:play_club_bgm()
                        v147 = false
                        if v148 then
                            v_u_35._env:update_club_uis(p137)
                            v151 = true
                        end;
                        if v146:contains(v_u_16.ZoneName.CompeteTower) then
                            v150 = true
                        end;
                    elseif v146:contains(v_u_16.ZoneName.CompeteTower) or v146:contains(v_u_16.ZoneName.GuildBuilding) then
                        v_u_35._bgm_manager:play_bgm(v_u_10.BGM_MATCHMAKING)
                        v150 = true
                        v147 = false
                    elseif v146:contains(v_u_16.ZoneName.MusicShop) or (v146:contains(v_u_16.ZoneName.GearShop) or v146:contains(v_u_16.ZoneName.Marketplace)) then
                        v_u_35._bgm_manager:play_bgm(v_u_10.BGM_SHOP)
                        v147 = false
                    end;
                    v_u_35._env:set_club_uis_visible(v151)
                    v_u_13:set_compete_building_uis_visible(v150)
                else
                    v147 = false
                end;
                if v147 == true then
                    v_u_35._bgm_manager:play_bgm(v_u_10.BGM_LOBBY)
                end;
                if p136._ui_manager:swallow_control_input() ~= true and (v_u_35._input:get_has_frame_focused_element() ~= true and v_u_35._input:control_just_pressed(v_u_3.KEY_CLICK)) then
                    local v152 = RaycastParams.new()
                    v152.FilterType = Enum.RaycastFilterType.Whitelist
                    v152.FilterDescendantsInstances = { v_u_13:get_lobby_characters_folder(), v_u_13:get_npc_root() }
                    v152.IgnoreWater = true
                    local v153 = v_u_1:get_camera():ScreenPointToRay(v_u_1:get_local_mouse().X, v_u_1:get_local_mouse().Y)
                    local v154 = workspace:Raycast(v153.Origin, v153.Direction * 50, v152)
                    if v154 and v154.Instance ~= nil then
                        for _, v155 in pairs(game.Players:GetPlayers()) do
                            if v155.Character ~= nil and v_u_1:has_ancestor_of(v154.Instance, v155.Character) then
                                local v156 = v_u_1:get_player_animator(v155)
                                if v156 == nil then
                                    return;
                                end;
                                for _, v157 in pairs(v156:GetPlayingAnimationTracks()) do
                                    if v157.Animation and v_u_18:singleton():assetid_is_dance(v157.Animation.AnimationId) then
                                        f_play_animation_synced_to_name(v157.Animation, v157.TimePosition, v155.Name)
                                        v_u_35._evt:fire_event_to_server(v_u_6.EVT_Lobby_ClientRequestSyncDanceToPlayer, v155.UserId)
                                        break;
                                    end;
                                end;
                                break;
                            end;
                        end;
                        for _, v158 in v_u_35._npcs:get_id_to_npcs():key_itr() do
                            local v159 = v158:get_root()
                            if v159 and v_u_1:has_ancestor_of(v154.Instance, v159) then
                                if v154.Instance:GetAttribute(v_u_13:get_no_trigger_dance_sync_attribute_name()) == nil then
                                    local v160 = v_u_1:first_child_of_type(v159, "Humanoid")
                                    if v160 then
                                        local v161 = v_u_1:first_child_of_type(v160, "Animator")
                                        if v161 then
                                            for _, v162 in pairs(v161:GetPlayingAnimationTracks()) do
                                                if v162.Animation and v_u_18:singleton():assetid_is_dance(v162.Animation.AnimationId) then
                                                    f_play_animation_synced_to_name(v162.Animation, v162.TimePosition, v159.Name)
                                                    break;
                                                end;
                                            end;
                                        end;
                                    end;
                                end;
                                break;
                            end;
                        end;
                    end;
                end;
            end;
            v_u_1:profileend()
        end;
        if v_u_35._current_mode ~= v_u_31.Mode.Cleanup then
            v_u_1:profilebegin("LobbyLocal:_ui_manager:update")
            v_u_35._ui_manager:update(p137, v_u_35)
            v_u_1:profileend()
            v_u_1:profilebegin("LobbyLocal:_env:update")
            p136._env:update(p137)
            v_u_1:profileend()
        end;
        if v_u_1:is_dev_build() and (p_u_34._input:control_just_released(v_u_3.KEY_DEBUG_2) and p_u_34._menus:top_menu_swallows_input() == false) then
            v_u_35._player_status_manager:log_debug_info()
        end;
        v_u_1:profileend()
    end;
    v_u_35.post_update = function(p163, p164) --[[ Name: post_update ]] --[[ Line: 723 ]]
        --[[ Upvalues: (copy 1): v_u_35, (ref 2): v_u_31 ]]
        if v_u_35._current_mode == v_u_31.Mode.Game then
            p163._npcs:update(p164)
        end;
        v_u_35._event_integration_manager:post_update(p164)
    end;
    v_u_35.save_camera_position = function(_) --[[ Name: save_camera_position ]] --[[ Line: 730 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_32, (ref 3): v_u_33 ]]
        local v165 = v_u_1:get_camera()
        if v165 then
            v_u_32 = true
            v_u_33 = v165.CFrame
        end;
    end;
    v_u_35.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 738 ]]
        --[[ Upvalues: (copy 1): v_u_38, (copy 2): v_u_35, (copy 3): f_cleanup_character_scripts, (ref 4): v_u_31 ]]
        for _, v166 in v_u_38:key_itr() do
            v166(v_u_35)
        end;
        if v_u_35._player_status_manager:is_playerlist_update_subscribed() then
            v_u_35._player_status_manager:set_playerlist_info_update_subscribed(false)
        end;
        v_u_35._npcs:cleanup()
        f_cleanup_character_scripts()
        v_u_35._current_mode = v_u_31.Mode.Cleanup
        v_u_35._event_integration_manager:cleanup()
    end;
    v_u_35.songkey_opt_set_artist_event_info = function(_, p167) --[[ Name: songkey_opt_set_artist_event_info ]] --[[ Line: 757 ]]
        --[[ Upvalues: (ref 1): v_u_20, (copy 2): v_u_35, (ref 3): v_u_28, (ref 4): v_u_1, (ref 5): v_u_8, (ref 6): v_u_17, (ref 7): v_u_29 ]]
        local v168, v169 = v_u_20:is_event_active(v_u_35._player_blob_manager:get_day_event_list())
        if v168 and v_u_20:get_playable_song_set(v169):contains(p167) then
            if v_u_35._game_join_protocol:get_event_info() == nil then
                v_u_35._game_join_protocol:set_event_info(v_u_28.EventMission.ArtistEvent)
                if v_u_1:is_dev_build() then
                    v_u_8:puts("LobbyLocal:songkey_opt_set_artist_event_info setting event info to ArtistEvent")
                end;
            end;
            if v_u_35._player_settings_manager:get_key(v_u_17.Key.ArtistEventUseStage) == true and v_u_20:get_event_info(v169):has_stage() then
                v_u_29:artist_event_set_custom_stage_id(v_u_20:get_event_info(v169):get_stage_id())
            end;
        end;
    end;
    v_u_35._current_mode = v_u_31.Mode.PreStart
    return v_u_35;
end;
return v_u_31;
