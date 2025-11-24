-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:13 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_4 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = nil
local v_u_7 = nil
v1:require_client(function() --[[ Line: 11 ]]
    --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7 ]]
    v_u_6 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_7 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
end)
local v_u_8 = {
    ["get_group_rewards_title_id"] = function(_) --[[ Name: get_group_rewards_title_id ]] --[[ Line: 18 ]]
        return 43;
    end,
    ["get_group_rewards_pet_id"] = function(_) --[[ Name: get_group_rewards_pet_id ]] --[[ Line: 19 ]]
        return 1;
    end
}
local v_u_9 = v5:new()
v_u_4.RewardInfo:add_rewards_list_from_table(v_u_9, {
    {
        ["Type"] = v_u_4.RewardType.Stars,
        ["Id"] = nil,
        ["Amount"] = 5
    },
    {
        ["Type"] = v_u_4.RewardType.Coins,
        ["Id"] = nil,
        ["Amount"] = 250
    },
    {
        ["Type"] = v_u_4.RewardType.Titles,
        ["Id"] = v_u_8:get_group_rewards_title_id(),
        ["Amount"] = 1
    },
    {
        ["Type"] = v_u_4.RewardType.Pet,
        ["Id"] = v_u_8:get_group_rewards_pet_id(),
        ["Amount"] = 1
    }
})
v_u_8.playerblob_has_claimed_group_rewards = function(_, p10) --[[ Name: playerblob_has_claimed_group_rewards ]] --[[ Line: 29 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_8 ]]
    return v_u_2:owns_title_id(p10, v_u_8:get_group_rewards_title_id());
end;
v_u_8.claim_group_rewards_button_pressed = function(_, p_u_11, p_u_12) --[[ Name: claim_group_rewards_button_pressed ]] --[[ Line: 33 ]]
    --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_3, (ref 3): v_u_7, (copy 4): v_u_9 ]]
    p_u_11._menus:push_menu(v_u_6:new(p_u_11, p_u_11._spui, p_u_11._menus)):set_text("Join the RobeatsDev Group for rewards!", "Get an exclusive title and a nice gift by joining the RobeatsDev group! Press \'Okay\' to claim your reward."):set_okay_button_fn(function() --[[ Line: 36 ]]
        --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_6, (ref 3): v_u_3, (ref 4): v_u_7, (ref 5): v_u_9, (copy 6): p_u_12 ]]
        local v_u_13 = p_u_11._menus:push_menu(v_u_6:new(p_u_11, p_u_11._spui, p_u_11._menus)):set_text("Loading...", ""):set_close_button_visible(false)
        p_u_11._evt:wait_on_event_once(v_u_3.EVT_RobloxGroup_ServerClaimResponse, function(p14, p15) --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): p_u_11, (copy 2): v_u_13, (ref 3): v_u_6, (ref 4): v_u_7, (ref 5): v_u_9, (ref 6): p_u_12 ]]
            if p14 == true then
                p_u_11._player_blob_manager:do_sync(function() --[[ Line: 47 ]]
                    --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_13, (ref 3): v_u_7, (ref 4): v_u_9, (ref 5): p_u_12 ]]
                    p_u_11._menus:remove_menu(v_u_13)
                    p_u_11._menus:push_menu(v_u_7:new(p_u_11, p_u_11._spui, p_u_11._menus, v_u_9):set_header_text("Success!"):set_sub_text(string.format("For joining the RobeatsDev group, you have received...")))
                    if p_u_12 then
                        p_u_12()
                    end;
                end)
            else
                p_u_11._menus:remove_menu(v_u_13)
                p_u_11._menus:push_menu(v_u_6:new(p_u_11, p_u_11._spui, p_u_11._menus)):set_text("Error", p15)
            end;
        end)
        p_u_11._evt:fire_event_to_server(v_u_3.EVT_RobloxGroup_ClientClaim)
    end)
end;
v_u_8.apply_rewards_to_playerblob = function(_, p16, p17) --[[ Name: apply_rewards_to_playerblob ]] --[[ Line: 65 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_9 ]]
    return v_u_4:claim_reward_info_list_to_playerblob(p16, p17, v_u_9);
end;
local v_u_18 = true
v_u_8.get_notification_state = function(_) --[[ Name: get_notification_state ]] --[[ Line: 71 ]]
    --[[ Upvalues: (ref 1): v_u_18 ]]
    return v_u_18;
end;
v_u_8.set_notification_state = function(_, p19) --[[ Name: set_notification_state ]] --[[ Line: 72 ]]
    --[[ Upvalues: (ref 1): v_u_18 ]]
    v_u_18 = p19
end;
return v_u_8;
