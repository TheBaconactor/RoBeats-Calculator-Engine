-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:49 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_12 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistP3EventInfo)
local v14 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
local v_u_19 = nil
v14:require_client(function() --[[ Line: 28 ]]
    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): v_u_17, (ref 4): v_u_18, (ref 5): v_u_19 ]]
    v_u_15 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.UI.MatchMakingV3GameStageSelectSection)
    v_u_18 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
    v_u_19 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
end)
local v20 = {}
local v_u_21 = 0
v20.new = function(_, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 41 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_13, (copy 6): v_u_9, (copy 7): v_u_10, (copy 8): v_u_8, (ref 9): v_u_21, (ref 10): v_u_15, (ref 11): v_u_18, (ref 12): v_u_19, (copy 13): v_u_6, (copy 14): v_u_11, (copy 15): v_u_12, (ref 16): v_u_17, (ref 17): v_u_16, (copy 18): v_u_1, (copy 19): v_u_7 ]]
    local v_u_25 = v_u_2:new(p_u_23, p_u_24)
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_26, (copy 2): v_u_25, (copy 3): p_u_22, (ref 4): v_u_30, (ref 5): v_u_4, (ref 6): v_u_3, (copy 7): p_u_23, (ref 8): v_u_5, (copy 9): p_u_24, (ref 10): v_u_29, (ref 11): v_u_27, (ref 12): v_u_13, (ref 13): v_u_9, (ref 14): v_u_10, (ref 15): v_u_8, (ref 16): v_u_21, (ref 17): v_u_15, (ref 18): v_u_18, (ref 19): v_u_19, (ref 20): v_u_28, (ref 21): v_u_6, (ref 22): v_u_31, (ref 23): v_u_11, (ref 24): v_u_12, (ref 25): v_u_17, (ref 26): v_u_16 ]]
        v_u_26 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.GenericArtistP3EventUI:Clone()
        v_u_25:set_showing(true)
        local v_u_32 = p_u_22._player_blob_manager:get_player_blob()
        v_u_30 = p_u_22._bgm_manager:begin_preview_songkey()
        v_u_25._native_size = v_u_26.PrimaryPart.Size
        v_u_25._size = v_u_25._native_size
        v_u_25:add_cycle_element(p_u_22, 1, v_u_4:new(v_u_3:new(v_u_25, v_u_26.PrimaryPart, v_u_26.BackButtonSurface), p_u_23, function() --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_5, (ref 3): p_u_24, (ref 4): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_5.SFX_MENU_CLOSE)
            p_u_24:remove_menu(v_u_25)
        end))
        local l_LoadedSection_0 = v_u_26.MainSurface.SurfaceGui.Frame.LoadedSection
        v_u_29 = l_LoadedSection_0.RewardSection.CountDisplay
        v_u_29.Text = ""
        local l_SongPageDisplay_0 = l_LoadedSection_0.SongPageDisplay
        local v_u_33 = v_u_25:add_cycle_element(p_u_22, 1, v_u_4:new(v_u_3:new(v_u_25, v_u_26.PrimaryPart, v_u_26.ArrowLeft), p_u_23, function() --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_5, (ref 3): v_u_27 ]]
            p_u_22._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_27:prev_page()
        end))
        local v_u_34 = v_u_25:add_cycle_element(p_u_22, 1, v_u_4:new(v_u_3:new(v_u_25, v_u_26.PrimaryPart, v_u_26.ArrowRight), p_u_23, function() --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_5, (ref 3): v_u_27 ]]
            p_u_22._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_27:next_page()
        end))
        local v_u_35 = v_u_13:get_playable_song_set():key_list()
        v_u_35:sort(function(p36, p37) --[[ Line: 108 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9:singleton():get_difficulty_for_key(p37) - v_u_9:singleton():get_difficulty_for_key(p36);
        end)
        local v_u_38 = v_u_10:new(p_u_22, v_u_26.SongElementDisplay, v_u_3:new(v_u_25, v_u_26.PrimaryPart, v_u_26.SongElementDisplay.PrimaryPart))
        v_u_27 = v_u_8:new():set_fn_get_data_list(function() --[[ Line: 119 ]]
            --[[ Upvalues: (copy 1): v_u_35 ]]
            return v_u_35;
        end):set_fn_set_element_data(function(p39, p40) --[[ Line: 122 ]]
            --[[ Upvalues: (ref 1): p_u_22 ]]
            p39:display_song(p40)
            p_u_22._bgm_manager:preview_songkey(p40)
        end):set_fn_next_prev_visible(function(p41, p42) --[[ Line: 126 ]]
            --[[ Upvalues: (copy 1): v_u_34, (copy 2): v_u_33 ]]
            v_u_34:set_visible(p41)
            v_u_33:set_visible(p42)
        end):set_fn_update_page_display(function(p43, p44) --[[ Line: 130 ]]
            --[[ Upvalues: (copy 1): l_SongPageDisplay_0 ]]
            l_SongPageDisplay_0.Text = string.format("Song %d (of %d)", p43, p44)
        end):set_do_wrap(true):set_i_offset(v_u_21):set_fn_store_i_offset(function(p45) --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21 = p45
        end)
        v_u_27:push_display_element(v_u_38)
        v_u_27:page_update()
        v_u_25:add_cycle_element(p_u_22, 1, v_u_4:new(v_u_3:new(v_u_25, v_u_26.PrimaryPart, v_u_26.SongInfoButton), p_u_23, function() --[[ Line: 145 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_5, (copy 3): v_u_38, (ref 4): v_u_9, (ref 5): v_u_13, (copy 6): v_u_32, (ref 7): v_u_10 ]]
            p_u_22._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            local v46 = v_u_38:get_element_data()
            local v47 = v_u_9:singleton():get_audiomod_to_modes_of_songkey(v46)
            local v48
            if v47:contains(v_u_9.MOD_NORMAL) then
                local v49 = "<b>Collected Normal Mode</b>: "
                if v_u_13:playerblob_owns_song(v_u_32, v47:get(v_u_9.MOD_NORMAL), nil, p_u_22._player_blob_manager:get_cached_collection_info()) then
                    v48 = v49 .. "Yes"
                else
                    v48 = v49 .. "No"
                end;
            else
                v48 = ""
            end;
            v_u_10:show_song_info_popup(p_u_22, v46, nil, v48)
        end))
        local function f_claim_button_handle_response(p50, p51) --[[ Name: claim_button_handle_response ]] --[[ Line: 169 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_5, (ref 3): v_u_15, (ref 4): p_u_23, (ref 5): p_u_24, (ref 6): v_u_18, (ref 7): v_u_19 ]]
            p_u_22._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            local v_u_52 = p_u_22._menus:push_menu(v_u_15:new(p_u_22, p_u_23, p_u_24):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_22._evt:wait_on_event_once(p51, function(p53, p_u_54, p_u_55) --[[ Line: 176 ]]
                --[[ Upvalues: (ref 1): p_u_22, (copy 2): v_u_52, (ref 3): p_u_24, (ref 4): v_u_15, (ref 5): p_u_23, (ref 6): v_u_5, (ref 7): v_u_18, (ref 8): v_u_19 ]]
                if p53 == true then
                    local v_u_56 = nil
                    pcall(function() --[[ Line: 185 ]]
                        --[[ Upvalues: (ref 1): v_u_56, (ref 2): v_u_18, (copy 3): p_u_55 ]]
                        v_u_56 = v_u_18.RewardInfo:table_to_list(p_u_55)
                    end)
                    p_u_22._player_blob_manager:do_sync(function(_) --[[ Line: 189 ]]
                        --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_52, (ref 3): v_u_56, (ref 4): p_u_24, (ref 5): v_u_19, (ref 6): p_u_23, (ref 7): v_u_15, (copy 8): p_u_54, (ref 9): v_u_5 ]]
                        p_u_22._menus:remove_menu(v_u_52)
                        if v_u_56 == nil or v_u_56:count() <= 0 then
                            p_u_22._menus:push_menu(v_u_15:new(p_u_22, p_u_23, p_u_24):set_text("Claimed Reward!", p_u_54))
                            p_u_22._sfx_manager:play_sfx(v_u_5.SFX_ACQUIRE)
                        else
                            p_u_24:push_menu(v_u_19:new(p_u_22, p_u_23, p_u_24, v_u_56))
                        end;
                    end)
                else
                    p_u_22._menus:remove_menu(v_u_52)
                    p_u_24:push_menu(v_u_15:new(p_u_22, p_u_23, p_u_24):set_text("Failed", p_u_54))
                    p_u_22._sfx_manager:play_sfx(v_u_5.SFX_FAIL)
                end;
            end)
            p_u_22._evt:fire_event_to_server(p50)
        end;
        v_u_28 = v_u_25:add_cycle_element(p_u_22, 1, v_u_4:new(v_u_3:new(v_u_25, v_u_26.PrimaryPart, v_u_26.ClaimButton), p_u_23, function() --[[ Line: 210 ]]
            --[[ Upvalues: (copy 1): f_claim_button_handle_response, (ref 2): v_u_6 ]]
            f_claim_button_handle_response(v_u_6.EVT_SpecialEvent_GenericArtistP3Claim_Client, v_u_6.EVT_SpecialEvent_GenericArtistP3Claim_Server)
        end))
        v_u_4:button_add_enabled_anim(v_u_28, function() --[[ Line: 217 ]]
            --[[ Upvalues: (ref 1): v_u_25 ]]
            return v_u_25:get_alpha();
        end)
        if v_u_13:external_badge_reward_enabled() then
            v_u_31 = v_u_25:add_cycle_element(p_u_22, 1, v_u_4:new(v_u_3:new(v_u_25, v_u_26.PrimaryPart, v_u_26.ClaimBadgeRewardButton), p_u_23, function() --[[ Line: 223 ]]
                --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_5, (ref 3): v_u_15, (ref 4): p_u_23, (ref 5): p_u_24, (copy 6): f_claim_button_handle_response, (ref 7): v_u_6 ]]
                p_u_22._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
                p_u_22._menus:push_menu(v_u_15:new(p_u_22, p_u_23, p_u_24):set_text("No-Scope Arcade Rewards", "Get the RoBeats badge in \'No-Scope Arcade\' to claim the reward! Get 10 kills with any of the RoBeats-themed weapon skins. Press Okay to claim this reward."):set_okay_button_fn(function() --[[ Line: 230 ]]
                    --[[ Upvalues: (ref 1): f_claim_button_handle_response, (ref 2): v_u_6 ]]
                    f_claim_button_handle_response(v_u_6.EVT_SpecialEvent_GenericArtistP3ClaimBadgeReward_Client, v_u_6.EVT_SpecialEvent_GenericArtistP3ClaimBadgeReward_Server)
                end))
            end))
            v_u_4:button_add_enabled_anim(v_u_31, function() --[[ Line: 239 ]]
                --[[ Upvalues: (ref 1): v_u_25 ]]
                return v_u_25:get_alpha();
            end)
        end;
        v_u_25:update_claim_button_status()
        v_u_25:add_cycle_element(p_u_22, 1, v_u_4:new(v_u_3:new(v_u_25, v_u_26.PrimaryPart, v_u_26.PlayButton), p_u_23, function() --[[ Line: 247 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_5, (ref 3): v_u_11, (ref 4): v_u_12, (ref 5): v_u_17, (ref 6): v_u_13, (ref 7): v_u_16, (copy 8): v_u_38 ]]
            p_u_22._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
            p_u_22._game_join_protocol:set_event_info(v_u_11.EventMission.GenericArtistP3Event)
            if p_u_22._player_settings_manager:get_key(v_u_12.Key.ArtistEventUseStage) == true then
                v_u_17:artist_event_set_custom_stage_id(v_u_13:get_stage_id())
            end;
            p_u_22._menus:push_menu(v_u_16:new(p_u_22, p_u_22._spui, p_u_22._menus, v_u_38:get_element_data()))
        end))
        local v57 = v_u_26:FindFirstChild("ButtonA")
        if v57 then
            v_u_25:add_cycle_element(p_u_22, 1, v_u_4:new(v_u_3:new(v_u_25, v_u_26.PrimaryPart, v57), p_u_23, function() --[[ Line: 268 ]]
                --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_5, (ref 3): v_u_15, (ref 4): p_u_23, (ref 5): p_u_24, (ref 6): v_u_13, (copy 7): v_u_32 ]]
                local v58 = p_u_22._player_blob_manager:get_cached_collection_info()
                p_u_22._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
                p_u_22._menus:push_menu(v_u_15:new(p_u_22, p_u_23, p_u_24):set_text("No-Scope Arcade Event", string.format("Play a song to receive a copy of the Normal mode. Collect %d of the Normal mode songs to be able to claim the reward, which will also grant the achievement. This achievement will get you rewards in No-Scope Arcade as well. Owned Event Songs: %d\nCollect Songs Reward Claimed: %s\nGear Claimed: %s\nStage Claimed: %s\nNo-Scope Arcade Badge Reward Claimed: %s", v_u_13:get_required_song_set_owned_count(), v_u_13:get_playerblob_owned_required_song_count(v_u_32, p_u_22._player_blob_manager:get_cached_collection_info()), tostring(v_u_13:test_playerblob_has_claimed_reward(v_u_32, v58)), tostring(v_u_13:test_playerblob_has_claimed_gear_reward(v_u_32)), tostring(v_u_13:test_playerblob_has_claimed_stage_reward(v_u_32, v58)), (tostring(v_u_13:test_playerblob_has_claimed_external_badge_reward(v_u_32, v58))))))
            end))
        end;
        local v59 = v_u_26:FindFirstChild("ButtonB")
        if v59 then
            v_u_25:add_cycle_element(p_u_22, 1, v_u_4:new(v_u_3:new(v_u_25, v_u_26.PrimaryPart, v59), p_u_23, function() --[[ Line: 295 ]]
                --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_5, (ref 3): v_u_15, (ref 4): p_u_23, (ref 5): p_u_24, (ref 6): v_u_6 ]]
                p_u_22._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
                p_u_22._menus:push_menu(v_u_15:new(p_u_22, p_u_23, p_u_24):set_text("Confirm", "Teleport to No-Scope Arcade?"):set_okay_button_fn(function() --[[ Line: 301 ]]
                    --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_15, (ref 3): p_u_23, (ref 4): p_u_24, (ref 5): v_u_6 ]]
                    p_u_22._menus:push_menu(v_u_15:new(p_u_22, p_u_23, p_u_24):set_text("Loading...", "Please wait..."))
                    p_u_22._evt:fire_event_to_server(v_u_6.EVT_SpecialEvent_GenericArtistP3Teleport_Client)
                end))
            end))
        end;
        v_u_25:transition_update_visual(0)
        v_u_25:layout()
    end;
    v_u_25.update_claim_button_status = function(_) --[[ Name: update_claim_button_status ]] --[[ Line: 315 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_13, (ref 3): v_u_29, (ref 4): v_u_28, (ref 5): v_u_31 ]]
        local v60 = p_u_22._player_blob_manager:get_player_blob()
        local v61 = v_u_13:get_playerblob_owned_required_song_count(v60, p_u_22._player_blob_manager:get_cached_collection_info())
        local v62 = v_u_13:get_required_song_set_owned_count()
        v_u_29.Text = string.format("Collected: %d of %d Songs (Required: %d)", v61, v_u_13:get_required_song_set():count(), v62)
        if v_u_13:test_playerblob_has_claimed_reward(v60) then
            v_u_28:set_enabled(false)
        elseif v61 < v62 then
            v_u_28:set_enabled(false)
        else
            v_u_28:set_enabled(true)
        end;
        if v_u_31 then
            if v_u_13:test_playerblob_has_claimed_external_badge_reward(v60, p_u_22._player_blob_manager:get_cached_collection_info()) then
                v_u_31:set_enabled(false)
                return;
            end;
            v_u_31:set_enabled(true)
        end;
    end;
    v_u_25.on_refocus = function(p63) --[[ Name: on_refocus ]] --[[ Line: 347 ]]
        p63:update_claim_button_status()
    end;
    v_u_25.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 351 ]]
        --[[ Upvalues: (ref 1): v_u_26, (copy 2): p_u_22, (ref 3): v_u_30 ]]
        v_u_26:Destroy()
        p_u_22._bgm_manager:stop_song_preview(v_u_30)
    end;
    v_u_25.behaviour_update = function(p64, p65, _) --[[ Name: behaviour_update ]] --[[ Line: 356 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_27 ]]
        p64:behaviour_update_base(p65, p_u_22)
        for _, v66 in v_u_27:get_display_elements():key_itr() do
            v66:behaviour_update(p65)
        end;
    end;
    local v_u_67 = 1
    local v_u_68 = 1
    v_u_25.layout = function(p69) --[[ Name: layout ]] --[[ Line: 365 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_68, (ref 3): v_u_26, (ref 4): v_u_27 ]]
        p69:opt_rescale_to_max_nxy(p_u_23, 0.8, 0.8, v_u_68)
        local v70, v71 = p69:opt_update_cframe_params(p_u_23, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p69:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v70 == true then
            v_u_26:SetPrimaryPartCFrame(v71)
        end;
        v_u_27:layout()
    end;
    v_u_25.set_alpha = function(_, p72) --[[ Name: set_alpha ]] --[[ Line: 378 ]]
        --[[ Upvalues: (ref 1): v_u_67, (ref 2): v_u_1, (ref 3): v_u_26 ]]
        if v_u_67 ~= p72 then
            v_u_67 = p72
            v_u_1:r_set_alpha(v_u_26, v_u_67)
        end;
    end;
    v_u_25.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 384 ]]
        --[[ Upvalues: (ref 1): v_u_67 ]]
        return v_u_67;
    end;
    v_u_25.set_scale = function(_, p73) --[[ Name: set_scale ]] --[[ Line: 385 ]]
        --[[ Upvalues: (ref 1): v_u_68 ]]
        v_u_68 = p73
    end;
    v_u_25.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 386 ]]
        --[[ Upvalues: (ref 1): v_u_68 ]]
        return v_u_68;
    end;
    v_u_25.get_native_size = function(p74) --[[ Name: get_native_size ]] --[[ Line: 388 ]]
        return p74._native_size;
    end;
    v_u_25.get_size = function(p75) --[[ Name: get_size ]] --[[ Line: 391 ]]
        return p75._size;
    end;
    v_u_25.set_size = function(p76, p77) --[[ Name: set_size ]] --[[ Line: 394 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        p76._size = p77
        v_u_26.PrimaryPart.Size = Vector3.new(p77.X, p77.Y, 0)
    end;
    v_u_25.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 398 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26.PrimaryPart.Position;
    end;
    v_u_25.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 401 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26.PrimaryPart.SurfaceGui;
    end;
    v_u_25.set_showing = function(_, p78) --[[ Name: set_showing ]] --[[ Line: 404 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_7 ]]
        if p78 then
            v_u_26.Parent = v_u_7:get_world_ui_folder()
        else
            v_u_26.Parent = nil
        end;
    end;
    f_cons()
    return v_u_25;
end;
return v20;
