-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:07 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v6 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_7 = nil
local v_u_8 = nil
v6:require_client(function() --[[ Line: 12 ]]
    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8 ]]
    v_u_7 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
    v_u_8 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
end)
return {
    ["purchase_prompt"] = function(_, p_u_9, p_u_10, p_u_11, p12, p_u_13) --[[ Name: purchase_prompt ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): v_u_5, (ref 6): v_u_7, (ref 7): v_u_8 ]]
        v_u_3:is_enum_member(p12, v_u_2)
        local v_u_14 = 0
        local v_u_15 = nil
        v_u_15 = p_u_9._menus:push_menu(v_u_1:new(p_u_9, p_u_10, p_u_11):set_text("", "Loading..."):set_title_sub_visible(false):set_close_button_visible(false):set_update_fn(function(p16) --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_4, (ref 3): v_u_15 ]]
            v_u_14 = v_u_14 + v_u_4:TimescaleToDeltaTime(p16)
            if v_u_14 > 3 then
                v_u_15:set_close_button_visible(true)
            end;
        end))
        p_u_9._player_blob_manager:set_iap_finish_fn(function(p17, p18, p19, p20) --[[ Line: 36 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_15, (ref 3): v_u_5, (ref 4): v_u_7, (ref 5): v_u_8, (copy 6): p_u_9, (copy 7): p_u_10, (ref 8): v_u_2, (ref 9): v_u_1, (copy 10): p_u_13 ]]
            p_u_11:remove_menu(v_u_15)
            if v_u_5.UseRewardDescriptionInfoAcquiredUI == true then
                p_u_11:push_menu(v_u_8:new(p_u_9, p_u_10, p_u_11, (v_u_7.RewardInfo:table_to_list(p20))):set_header_text("Purchased!"):set_sub_text("Purchased the following items..."))
            else
                if p18 ~= true then
                    p19 = v_u_2:get_description_for_productid(p17)
                end;
                p_u_11:push_menu(v_u_1:new(p_u_9, p_u_10, p_u_11):set_text("Purchase Complete!", p19))
            end;
            p_u_13()
        end)
        p_u_9._player_blob_manager:prompt_product_purchase(p12)
    end
};
