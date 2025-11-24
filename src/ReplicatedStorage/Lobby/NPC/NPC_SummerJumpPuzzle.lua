-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:38 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
local v1 = require(game.ReplicatedStorage.Shared.Dependency)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_4 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_6 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.JumpChallengeLocalUtil)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.JumpChallengeInfo)
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
v1:require_client(function() --[[ Line: 27 ]]
    --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_13, (ref 4): v_u_14, (ref 5): v_u_15, (ref 6): v_u_16, (ref 7): v_u_17 ]]
    v_u_11 = require(game.ReplicatedStorage.LocalShared.IntersectZoneManager)
    v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
    v_u_13 = require(game.ReplicatedStorage.Shared.InputUtil)
    v_u_14 = require(game.ReplicatedStorage.Lobby.NPC.NPCDialogPrompt)
    v_u_15 = require(game.ReplicatedStorage.Local.SFXManager)
    v_u_16 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
end)
return {
    ["create_npc"] = function(_, p_u_18, p_u_19) --[[ Name: create_npc ]] --[[ Line: 39 ]]
        --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_5, (copy 3): v_u_9, (copy 4): v_u_2, (copy 5): v_u_8, (ref 6): v_u_12, (ref 7): v_u_14, (copy 8): v_u_7, (ref 9): v_u_15, (ref 10): v_u_16, (copy 11): v_u_10, (copy 12): v_u_3, (copy 13): v_u_4, (ref 14): v_u_17 ]]
        v_u_5:singleton():load_model_category(v_u_6:get_category_name_to_id(v_u_6.Category.LobbyDecoration):get("JumpChallengeSummer"), v_u_6.Category.LobbyDecoration, function(p_u_20) --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_2, (copy 3): p_u_18, (ref 4): v_u_8, (ref 5): v_u_12, (ref 6): v_u_14, (copy 7): p_u_19, (ref 8): v_u_7, (ref 9): v_u_15, (ref 10): v_u_16, (ref 11): v_u_10, (ref 12): v_u_3, (ref 13): v_u_4, (ref 14): v_u_17 ]]
            local l_PlatformAnchors_0 = p_u_20.PlatformAnchors
            local v21 = v_u_9:spawn_anchor_root_with_name_to_proto_obj(l_PlatformAnchors_0, v_u_9:register_name_to_proto_obj_root(p_u_20.PlatformProto))
            local v_u_22 = v_u_2:new()
            local v_u_23 = nil
            for _, v24 in v21:key_itr() do
                local v25 = v24:FindFirstChild("BoostCollision")
                if v25 then
                    v25.Parent = nil
                    v_u_22:push_back(v25)
                end;
            end;
            local function v_u_26() --[[ Line: 59 ]]
                --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_9, (ref 3): p_u_18, (copy 4): v_u_22 ]]
                v_u_23 = v_u_9:register_boost_jump_on_collision_obj_list(p_u_18, 125, v_u_22)
            end;
            local v_u_27 = v_u_8:new()
            for _, v28 in pairs(p_u_20.CollectStars:GetChildren()) do
                v28.Parent = nil
                local v29 = tonumber(v28.Name)
                if v29 ~= nil then
                    v_u_27:add(v29, v28.PrimaryPart.CFrame)
                end;
            end;
            local v_u_30 = v_u_8:new()
            for v31, _ in v_u_27:key_itr() do
                v_u_30:add(v31, false)
            end;
            local function _() --[[ Name: get_collected_count ]] --[[ Line: 81 ]]
                --[[ Upvalues: (copy 1): v_u_30 ]]
                local v32 = 0
                for _, v33 in v_u_30:key_itr() do
                    if v33 == true then
                        v32 = v32 + 1
                    end;
                end;
                return v32;
            end;
            local v_u_34 = v_u_8:new()
            local v_u_35 = nil
            local function _(p36) --[[ Name: set_spawned_platform_enabled ]] --[[ Line: 94 ]]
                --[[ Upvalues: (ref 1): v_u_35, (copy 2): l_PlatformAnchors_0, (ref 3): v_u_12, (ref 4): v_u_23, (ref 5): v_u_26 ]]
                if v_u_35 == p36 then
                    return;
                else
                    v_u_35 = p36
                    if p36 then
                        l_PlatformAnchors_0.Parent = v_u_12:get_lobby_environment_no_popper()
                        if v_u_23 == nil then
                            v_u_26()
                        end;
                        v_u_23:set_enabled(true)
                    else
                        l_PlatformAnchors_0.Parent = nil
                        if v_u_23 then
                            v_u_23:set_enabled(false)
                        end;
                    end;
                end;
            end;
            if v_u_35 ~= false then
                v_u_35 = false
                l_PlatformAnchors_0.Parent = nil
                if v_u_23 then
                    v_u_23:set_enabled(false)
                end;
            end;
            local v_u_37 = nil
            v_u_37 = v_u_14:new(p_u_18, p_u_19, "NPC_SummerJumpPuzzle_Zara", "Summertime Zara", "Collect the Stars!", v_u_7:singleton():get_dance_assetid_for_id(5), function() --[[ Line: 124 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_15, (ref 3): v_u_35, (copy 4): v_u_27, (ref 5): v_u_14, (ref 6): p_u_19, (copy 7): v_u_30, (ref 8): v_u_16, (copy 9): v_u_34, (copy 10): l_PlatformAnchors_0, (ref 11): v_u_12, (ref 12): v_u_23, (ref 13): v_u_26, (ref 14): v_u_10, (ref 15): v_u_37, (ref 16): v_u_3, (ref 17): v_u_4, (ref 18): v_u_17 ]]
                p_u_18._sfx_manager:play_sfx(v_u_15.SFX_MENU_OPEN)
                if v_u_35 ~= true then
                    for v_u_38, v_u_39 in v_u_27:key_itr() do
                        local v_u_40 = nil
                        local v41 = v_u_14
                        local v42 = p_u_18
                        local v43 = p_u_19
                        local v44 = string.format("Star #%d", v_u_38)
                        local function v51() --[[ Line: 136 ]]
                            --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_15, (ref 3): v_u_30, (copy 4): v_u_38, (ref 5): v_u_40, (ref 6): v_u_16 ]]
                            p_u_18._sfx_manager:play_sfx(v_u_15.SFX_ACQUIRE)
                            v_u_30:add(v_u_38, true)
                            p_u_18._npcs:remove_npc(v_u_40)
                            local l__menus_0 = p_u_18._menus
                            local v45 = v_u_16:new(p_u_18, p_u_18._spui, p_u_18._menus)
                            local l_format_0 = string.format
                            local v46 = v_u_38
                            local v47 = 0
                            local v48 = "Found!"
                            local v49 = "You found Star #%d!\nYou\'ve found %d total Star(s)."
                            for _, v50 in v_u_30:key_itr() do
                                if v50 == true then
                                    v47 = v47 + 1
                                end;
                            end;
                            l__menus_0:push_menu(v45:set_text(v48, l_format_0(v49, v46, v47)))
                        end;
                        local v52 = {
                            ["NametagPositionOffset"] = Vector3.new(0, 2.5, 0)
                        }
                        v52.FnOnLoaded = function(_, p53, _) --[[ Name: FnOnLoaded ]] --[[ Line: 147 ]]
                            --[[ Upvalues: (copy 1): v_u_39 ]]
                            p53:SetPrimaryPartCFrame(v_u_39)
                        end;
                        v_u_40 = v41:new(v42, v43, "NPC_SummerJumpPuzzle_CollectStar", v44, "Collect Me!", nil, v51, v52)
                        v_u_34:add(v_u_38, v_u_40)
                        p_u_18._npcs:add_npc(v_u_40)
                    end;
                    if v_u_35 ~= true then
                        v_u_35 = true
                        l_PlatformAnchors_0.Parent = v_u_12:get_lobby_environment_no_popper()
                        if v_u_23 == nil then
                            v_u_26()
                        end;
                        v_u_23:set_enabled(true)
                    end;
                end;
                local function f_show_npc_message() --[[ Name: show_npc_message ]] --[[ Line: 159 ]]
                    --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_10, (ref 3): v_u_37 ]]
                    local v54 = 0
                    for _, v55 in v_u_30:key_itr() do
                        if v55 == true then
                            v54 = v54 + 1
                        end;
                    end;
                    if v54 < v_u_10:get_summer_beach_claim_reward1_count() then
                        v_u_37:display_msg(string.format("Up for a little beach-combing? We\'ve hidden a bunch of stars throughout the city. Come back when you\'ve found at least %d!", v_u_10:get_summer_beach_claim_reward1_count()))
                        return;
                    elseif v54 < v_u_10:get_summer_beach_claim_reward2_count() then
                        v_u_37:display_msg(string.format("Your next reward is at %d stars. Think you can find them?", v_u_10:get_summer_beach_claim_reward2_count()))
                        return;
                    elseif v54 < v_u_10:get_summer_beach_claim_reward3_count() then
                        v_u_37:display_msg(string.format("Your final reward is at %d stars. Think you can find them all?", v_u_10:get_summer_beach_claim_reward3_count()))
                    else
                        v_u_37:display_msg(string.format("You found all %d stars - Hope you enjoy my new icon, and have a great summer!", v_u_10:get_summer_beach_claim_reward3_count()))
                    end;
                end;
                local l__menus_1 = p_u_18._menus
                local l__spui_0 = p_u_18._spui
                local v_u_56 = l__menus_1:push_menu(v_u_16:new(p_u_18, l__spui_0, l__menus_1):set_text("Loading...", ""):set_close_button_visible(false))
                p_u_18._evt:wait_on_event_once(v_u_3.EVT_SummerJumpChallenge_ServerClaimReward, function(p57, p58, p59) --[[ Line: 175 ]]
                    --[[ Upvalues: (copy 1): f_show_npc_message, (copy 2): l__menus_1, (copy 3): v_u_56, (ref 4): v_u_16, (ref 5): p_u_18, (copy 6): l__spui_0, (ref 7): v_u_4, (ref 8): v_u_17 ]]
                    if p57 == true then
                        local v_u_60 = v_u_4.RewardInfo:table_to_list(p59)
                        if v_u_60:count() == 0 then
                            f_show_npc_message()
                            l__menus_1:remove_menu(v_u_56)
                        else
                            p_u_18._player_blob_manager:do_sync(function() --[[ Line: 189 ]]
                                --[[ Upvalues: (ref 1): l__menus_1, (ref 2): v_u_56, (ref 3): v_u_17, (ref 4): p_u_18, (ref 5): l__spui_0, (copy 6): v_u_60, (ref 7): f_show_npc_message ]]
                                l__menus_1:remove_menu(v_u_56)
                                l__menus_1:push_menu(v_u_17:new(p_u_18, l__spui_0, l__menus_1, v_u_60, function() --[[ Line: 192 ]]
                                    --[[ Upvalues: (ref 1): f_show_npc_message ]]
                                    f_show_npc_message()
                                end):set_header_text("Rewards"))
                            end)
                        end;
                    else
                        f_show_npc_message()
                        l__menus_1:remove_menu(v_u_56)
                        l__menus_1:push_menu(v_u_16:new(p_u_18, l__spui_0, l__menus_1):set_text("Failed", p58))
                        return;
                    end;
                end)
                local l__evt_0 = p_u_18._evt
                local l_EVT_SummerJumpChallenge_ClientClaimReward_0 = v_u_3.EVT_SummerJumpChallenge_ClientClaimReward
                local v61 = 0
                for _, v62 in v_u_30:key_itr() do
                    if v62 == true then
                        v61 = v61 + 1
                    end;
                end;
                l__evt_0:fire_event_to_server(l_EVT_SummerJumpChallenge_ClientClaimReward_0, v61)
            end)
            p_u_18._npcs:add_npc(v_u_37)
            p_u_18:register_lobby_exit_fn(function(_) --[[ Line: 205 ]]
                --[[ Upvalues: (ref 1): v_u_35, (copy 2): l_PlatformAnchors_0, (ref 3): v_u_23, (copy 4): p_u_20 ]]
                if v_u_35 ~= false then
                    v_u_35 = false
                    l_PlatformAnchors_0.Parent = nil
                    if v_u_23 then
                        v_u_23:set_enabled(false)
                    end;
                end;
                l_PlatformAnchors_0:Destroy()
                p_u_20:Destroy()
            end)
            p_u_20.Parent = v_u_12:get_lobby_environment()
        end)
    end
};
