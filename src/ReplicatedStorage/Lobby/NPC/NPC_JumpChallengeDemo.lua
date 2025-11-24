-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:37 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.Override)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v3 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_9 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.LocalShared.JumpChallengeLocalUtil)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.JumpChallengeInfo)
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
v3:require_client(function() --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): v_u_14, (ref 4): v_u_15, (ref 5): v_u_16, (ref 6): v_u_17, (ref 7): v_u_18 ]]
    v_u_12 = require(game.ReplicatedStorage.LocalShared.IntersectZoneManager)
    v_u_13 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_14 = require(game.ReplicatedStorage.Shared.InputUtil)
    v_u_15 = require(game.ReplicatedStorage.Lobby.NPC.NPCDialogPrompt)
    v_u_16 = require(game.ReplicatedStorage.Local.SFXManager)
    v_u_17 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_18 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
end)
return {
    ["create_npc"] = function(_, p_u_19, p_u_20) --[[ Name: create_npc ]] --[[ Line: 37 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_8, (ref 3): v_u_15, (ref 4): v_u_16, (copy 5): v_u_10, (copy 6): v_u_5, (ref 7): v_u_13, (ref 8): v_u_12, (copy 9): v_u_11, (ref 10): v_u_17, (copy 11): v_u_6, (ref 12): v_u_18, (copy 13): v_u_7, (copy 14): v_u_4, (copy 15): v_u_1, (ref 16): v_u_14, (copy 17): v_u_2 ]]
        v_u_8:singleton():load_model_category(v_u_9:get_category_name_to_id(v_u_9.Category.LobbyDecoration):get("JumpChallengeDemo"), v_u_9.Category.NPC, function(p_u_21) --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_19, (copy 3): p_u_20, (ref 4): v_u_16, (ref 5): v_u_10, (ref 6): v_u_5, (ref 7): v_u_13, (ref 8): v_u_12, (ref 9): v_u_11, (ref 10): v_u_17, (ref 11): v_u_6, (ref 12): v_u_18, (ref 13): v_u_7, (ref 14): v_u_4, (ref 15): v_u_1, (ref 16): v_u_14, (ref 17): v_u_2 ]]
            local v_u_22 = nil
            v_u_22 = v_u_15:new(p_u_19, p_u_20, "NPC_JumpChallengeDemo", "Jump Challenge", "Challenge Start!", "rbxassetid://5167774741", function() --[[ Line: 49 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_16, (ref 3): v_u_22 ]]
                p_u_19._sfx_manager:play_sfx(v_u_16.SFX_MENU_OPEN)
                v_u_22:display_msg("We\'ve got a new challenge for you... See you at the top!")
            end)
            p_u_19._npcs:add_npc(v_u_22)
            local l_PlatformAnchors_0 = p_u_21.PlatformAnchors
            local v23 = v_u_10:spawn_anchor_root_with_name_to_proto_obj(l_PlatformAnchors_0, v_u_10:register_name_to_proto_obj_root(p_u_21.PlatformProto))
            local v_u_24 = v_u_5:new()
            local v_u_25 = nil
            for _, v26 in v23:key_itr() do
                local v27 = v26:FindFirstChild("BoostCollision")
                if v27 then
                    v27.Parent = nil
                    v_u_24:push_back(v27)
                end;
            end;
            local function v_u_28() --[[ Line: 74 ]]
                --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_10, (ref 3): p_u_19, (copy 4): v_u_24 ]]
                v_u_25 = v_u_10:register_boost_jump_on_collision_obj_list(p_u_19, 125, v_u_24)
            end;
            local v_u_29 = nil
            local function _(p30) --[[ Name: set_spawned_platform_enabled ]] --[[ Line: 84 ]]
                --[[ Upvalues: (ref 1): v_u_29, (copy 2): l_PlatformAnchors_0, (ref 3): v_u_13, (ref 4): v_u_25, (ref 5): v_u_28 ]]
                if v_u_29 == p30 then
                    return;
                else
                    v_u_29 = p30
                    if p30 then
                        l_PlatformAnchors_0.Parent = v_u_13:get_lobby_environment_no_popper()
                        if v_u_25 == nil then
                            v_u_28()
                        end;
                        v_u_25:set_enabled(true)
                    else
                        l_PlatformAnchors_0.Parent = nil
                        if v_u_25 then
                            v_u_25:set_enabled(false)
                        end;
                    end;
                end;
            end;
            local v_u_31
            if v_u_29 == false then
                v_u_31 = v_u_29
            else
                v_u_29 = false
                l_PlatformAnchors_0.Parent = nil
                if v_u_25 then
                    v_u_25:set_enabled(false)
                    v_u_31 = v_u_29
                else
                    v_u_31 = v_u_29
                end;
            end;
            local v_u_32 = 0
            local v_u_33 = p_u_20._intersect_zone_manager:get_intersect_zone_for_zonename(v_u_12.ZoneName.OnGround)
            local l_BoostCollision_0 = p_u_21.Truck.BoostCollision
            l_BoostCollision_0.Parent = nil
            local v_u_34 = nil
            local v_u_35 = false
            local function f_start_spawned_platforms(p_u_36) --[[ Name: start_spawned_platforms ]] --[[ Line: 111 ]]
                --[[ Upvalues: (ref 1): v_u_31, (copy 2): l_PlatformAnchors_0, (ref 3): v_u_13, (ref 4): v_u_25, (ref 5): v_u_28, (ref 6): v_u_32, (ref 7): v_u_35, (ref 8): v_u_34, (ref 9): v_u_15, (ref 10): p_u_20, (ref 11): v_u_16, (ref 12): v_u_11, (ref 13): v_u_17, (ref 14): v_u_6, (ref 15): v_u_18, (ref 16): v_u_7 ]]
                local l__menus_0 = p_u_36._menus
                local l__spui_0 = p_u_36._spui
                if v_u_31 ~= true then
                    v_u_31 = true
                    l_PlatformAnchors_0.Parent = v_u_13:get_lobby_environment_no_popper()
                    if v_u_25 == nil then
                        v_u_28()
                    end;
                    v_u_25:set_enabled(true)
                end;
                v_u_32 = 0
                v_u_35 = false
                if v_u_34 == nil then
                    v_u_34 = v_u_15:new(p_u_36, p_u_20, "NPC_JumpChallengeDemoGoal", "Jump Challenge", "Goal!", "rbxassetid://6399401447", function() --[[ Line: 127 ]]
                        --[[ Upvalues: (ref 1): v_u_34, (copy 2): p_u_36, (ref 3): v_u_16, (ref 4): v_u_31, (ref 5): v_u_35, (ref 6): v_u_32, (ref 7): v_u_11, (copy 8): l__menus_0, (ref 9): v_u_17, (copy 10): l__spui_0, (ref 11): v_u_6, (ref 12): v_u_18, (ref 13): v_u_7 ]]
                        if v_u_34 == nil then
                            return;
                        else
                            p_u_36._sfx_manager:play_sfx(v_u_16.SFX_MENU_OPEN)
                            if v_u_31 == true then
                                v_u_35 = true
                                v_u_32 = math.max(v_u_32, 0.5)
                                local function _() --[[ Name: show_npc_message ]] --[[ Line: 135 ]]
                                    --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_32 ]]
                                    v_u_34:display_msg(string.format("You made it to the top in %.1f seconds, nice work! Hope you aren\'t afraid of heights...", v_u_32))
                                end;
                                if v_u_11:playerblob_has_claimed_jump_challenge_1_reward((p_u_36._player_blob_manager:get_player_blob())) then
                                    v_u_34:display_msg(string.format("You made it to the top in %.1f seconds, nice work! Hope you aren\'t afraid of heights...", v_u_32))
                                else
                                    local v_u_37 = l__menus_0:push_menu(v_u_17:new(p_u_36, l__spui_0, l__menus_0):set_text("Loading...", ""):set_close_button_visible(false))
                                    p_u_36._evt:wait_on_event_once(v_u_6.EVT_JumpChallenge_ServerClaimReward, function(p38, p39, p_u_40) --[[ Line: 143 ]]
                                        --[[ Upvalues: (ref 1): l__menus_0, (copy 2): v_u_37, (ref 3): v_u_17, (ref 4): p_u_36, (ref 5): l__spui_0, (ref 6): v_u_18, (ref 7): v_u_7, (ref 8): v_u_34, (ref 9): v_u_32 ]]
                                        if p38 == true then
                                            p_u_36._player_blob_manager:do_sync(function() --[[ Line: 149 ]]
                                                --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_37, (ref 3): v_u_18, (ref 4): p_u_36, (ref 5): l__spui_0, (ref 6): v_u_7, (copy 7): p_u_40, (ref 8): v_u_34, (ref 9): v_u_32 ]]
                                                l__menus_0:remove_menu(v_u_37)
                                                l__menus_0:push_menu(v_u_18:new(p_u_36, l__spui_0, l__menus_0, v_u_7.RewardInfo:table_to_list(p_u_40), function() --[[ Line: 152 ]]
                                                    --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_32 ]]
                                                    v_u_34:display_msg(string.format("You made it to the top in %.1f seconds, nice work! Hope you aren\'t afraid of heights...", v_u_32))
                                                end):set_header_text("You reached the top!"):set_sub_text("Acquired..."))
                                            end)
                                        else
                                            l__menus_0:remove_menu(v_u_37)
                                            l__menus_0:push_menu(v_u_17:new(p_u_36, l__spui_0, l__menus_0):set_text("Failed", p39))
                                        end;
                                    end)
                                    p_u_36._evt:fire_event_to_server(v_u_6.EVT_JumpChallenge_ClientClaimReward, v_u_11:get_jump_challenge_1_id())
                                end;
                            else
                                return v_u_34:display_msg("Touched the ground - that doesn\'t count! (No cheating)");
                            end;
                        end;
                    end)
                    p_u_36._npcs:add_npc(v_u_34)
                end;
            end;
            v_u_10:register_boost_jump_on_collision_obj_list(p_u_19, 175, v_u_5:new({ l_BoostCollision_0 }), function(_, p41) --[[ Line: 172 ]]
                --[[ Upvalues: (copy 1): f_start_spawned_platforms ]]
                f_start_spawned_platforms(p41)
            end)
            p_u_19:register_lobby_update_fn(function(p42, p43) --[[ Line: 177 ]]
                --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_35, (ref 3): v_u_32, (ref 4): v_u_4, (copy 5): v_u_33, (ref 6): v_u_1, (copy 7): l_PlatformAnchors_0, (ref 8): v_u_25, (ref 9): p_u_20, (ref 10): v_u_14, (copy 11): f_start_spawned_platforms, (ref 12): v_u_2 ]]
                if v_u_31 then
                    if v_u_35 ~= true then
                        v_u_32 = v_u_32 + v_u_4:TimescaleToDeltaTime(p42)
                    end;
                    if v_u_32 >= 0.5 and (v_u_33:contains_point(v_u_1:get_localplayer_cframe().Position) and v_u_31 ~= false) then
                        v_u_31 = false
                        l_PlatformAnchors_0.Parent = nil
                        if v_u_25 then
                            v_u_25:set_enabled(false)
                        end;
                    end;
                end;
                if v_u_1:is_dev_build() and (p_u_20._menus:top_menu_swallows_input() == false and p43._input:control_just_released(v_u_14.KEY_DEBUG_1)) then
                    p43._control_script:set_next_jump_as_boosted(true, 250)
                    p43._control_script:force_jump()
                    f_start_spawned_platforms(p43)
                    v_u_2:warnf("DEBUG boost jump and spawn_platform")
                end;
            end)
            p_u_19:register_lobby_exit_fn(function(_) --[[ Line: 199 ]]
                --[[ Upvalues: (ref 1): v_u_31, (copy 2): l_PlatformAnchors_0, (ref 3): v_u_25, (ref 4): v_u_34, (copy 5): p_u_21 ]]
                if v_u_31 ~= false then
                    v_u_31 = false
                    l_PlatformAnchors_0.Parent = nil
                    if v_u_25 then
                        v_u_25:set_enabled(false)
                    end;
                end;
                v_u_34 = nil
                l_PlatformAnchors_0:Destroy()
                p_u_21:Destroy()
            end)
            p_u_21.Parent = v_u_13:get_lobby_environment()
        end)
    end
};
