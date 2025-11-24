-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:07 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_5 = nil
v1:require_client(function() --[[ Line: 7 ]]
    --[[ Upvalues: (ref 1): v_u_5 ]]
    v_u_5 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
end)
local v_u_7 = {
    ["get_premium_rewards_title_id"] = function(_) --[[ Name: get_premium_rewards_title_id ]] --[[ Line: 13 ]]
        return 17;
    end,
    ["get_premium_reward_vip_days_count"] = function(_) --[[ Name: get_premium_reward_vip_days_count ]] --[[ Line: 14 ]]
        return 3;
    end,
    ["player_is_roblox_premium"] = function(_, p6) --[[ Name: player_is_roblox_premium ]] --[[ Line: 16 ]]
        return p6.MembershipType == Enum.MembershipType.Premium;
    end
}
v_u_7.playerblob_has_claimed_premium_rewards = function(_, p8) --[[ Name: playerblob_has_claimed_premium_rewards ]] --[[ Line: 18 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_7 ]]
    return v_u_2:owns_title_id(p8, v_u_7:get_premium_rewards_title_id());
end;
v_u_7.claim_premium_rewards_button_pressed = function(_, p_u_9, p_u_10) --[[ Name: claim_premium_rewards_button_pressed ]] --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_7, (copy 3): v_u_3 ]]
    p_u_9._menus:push_menu(v_u_5:new(p_u_9, p_u_9._spui, p_u_9._menus)):set_text("Roblox Premium Rewards", string.format("Get a %d day of free trial of Robeats VIP with Roblox Premium (and a unique premium-only title). Claim now!", v_u_7:get_premium_reward_vip_days_count())):set_okay_button_fn(function() --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_5, (ref 3): v_u_3, (ref 4): v_u_7, (copy 5): p_u_10 ]]
        local v_u_11 = p_u_9._menus:push_menu(v_u_5:new(p_u_9, p_u_9._spui, p_u_9._menus)):set_text("Loading...", ""):set_close_button_visible(false)
        p_u_9._evt:wait_on_event_once(v_u_3.EVT_RobloxPremium_ServerClaimResponse, function(p12) --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): p_u_9, (copy 2): v_u_11, (ref 3): v_u_5, (ref 4): v_u_7, (ref 5): p_u_10 ]]
            if p12 == true then
                p_u_9._player_blob_manager:do_sync(function() --[[ Line: 34 ]]
                    --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_11, (ref 3): v_u_5, (ref 4): v_u_7, (ref 5): p_u_10 ]]
                    p_u_9._menus:remove_menu(v_u_11)
                    p_u_9._menus:push_menu(v_u_5:new(p_u_9, p_u_9._spui, p_u_9._menus)):set_text("Success!", string.format("Got \"Roblox Premium\" title and %d days of VIP. Thanks for playing Robeats!", v_u_7:get_premium_reward_vip_days_count()))
                    if p_u_10 then
                        p_u_10()
                    end;
                end)
            else
                p_u_9._menus:remove_menu(v_u_11)
            end;
        end)
        p_u_9._evt:fire_event_to_server(v_u_3.EVT_RobloxPremium_ClientClaim)
    end)
end;
v_u_7.apply_rewards_to_playerblob_dayid = function(_, p13, p14) --[[ Name: apply_rewards_to_playerblob_dayid ]] --[[ Line: 47 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_7, (copy 3): v_u_4 ]]
    v_u_2:add_title(p13, v_u_7:get_premium_rewards_title_id())
    v_u_2:set_title_id(p13, v_u_7:get_premium_rewards_title_id())
    v_u_4:playerblob_set_vip_day(p13, math.max(v_u_4:playerblob_get_vip_day(p13), p14) + v_u_7:get_premium_reward_vip_days_count())
end;
local v_u_15 = true
v_u_7.get_notification_state = function(_) --[[ Name: get_notification_state ]] --[[ Line: 57 ]]
    --[[ Upvalues: (ref 1): v_u_15 ]]
    return v_u_15;
end;
v_u_7.set_notification_state = function(_, p16) --[[ Name: set_notification_state ]] --[[ Line: 58 ]]
    --[[ Upvalues: (ref 1): v_u_15 ]]
    v_u_15 = p16
end;
return v_u_7;
