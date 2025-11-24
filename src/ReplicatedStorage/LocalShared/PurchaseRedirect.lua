-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:01 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_1 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfoRewardDescription)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.PlayerPolicy)
local v_u_15 = {
    ["new"] = function(_, p_u_8, p_u_9) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_3 ]]
        local v10 = {}
        v10.get_currency_type = function(_) --[[ Name: get_currency_type ]] --[[ Line: 24 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            return p_u_8;
        end;
        v10.get_currency_amount = function(_) --[[ Name: get_currency_amount ]] --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): p_u_9 ]]
            return p_u_9;
        end;
        v10.is_valid = function(_) --[[ Name: is_valid ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_3, (copy 3): p_u_9 ]]
            local v11
            if (p_u_8 == v_u_3.CurrencyType.Coins or p_u_8 == v_u_3.CurrencyType.Stars) and typeof(p_u_9) == "number" then
                v11 = p_u_9 > 0
            else
                v11 = false
            end;
            return v11;
        end;
        v10.title_str = function(_) --[[ Name: title_str ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_8 ]]
            return string.format("Not enough %s", v_u_3:currency_type_to_string(p_u_8));
        end;
        v10.desc_str = function(_) --[[ Name: desc_str ]] --[[ Line: 35 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_3, (copy 3): p_u_8 ]]
            return string.format("You require %d more %s to complete this purchase.", tonumber(p_u_9), v_u_3:currency_type_to_string(p_u_8));
        end;
        return v10;
    end,
    ["redirect_to_productid"] = function(_, p12) --[[ Name: redirect_to_productid ]] --[[ Line: 46 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_4, (copy 3): v_u_6, (copy 4): v_u_2, (copy 5): v_u_3 ]]
        local function f_get_productid_getamount(p13) --[[ Name: get_productid_getamount ]] --[[ Line: 47 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_4, (ref 3): v_u_6, (ref 4): v_u_2 ]]
            v_u_5:is_enum_member(p13, v_u_4)
            local v14 = v_u_6:get_reward_info_list_for_purchase_id(p13)
            if v14:count() == 0 then
                v_u_2:errf("PurchaseRedirect list(%d) count == 0", p13)
            end;
            if v14:count() > 1 then
                v_u_2:warnf("PurchaseRedirect list(%d) count > 1", p13)
            end;
            return v14:get(1):get_amount();
        end;
        if p12:get_currency_type() == v_u_3.CurrencyType.Stars then
            if p12:get_currency_amount() <= f_get_productid_getamount(v_u_4.ProductID_Star1_V3) then
                return v_u_4.ProductID_Star1_V3;
            elseif p12:get_currency_amount() <= f_get_productid_getamount(v_u_4.ProductID_Star2_V3) then
                return v_u_4.ProductID_Star2_V3;
            elseif p12:get_currency_amount() <= f_get_productid_getamount(v_u_4.ProductID_Star3_V3) then
                return v_u_4.ProductID_Star3_V3;
            else
                return v_u_4.ProductID_Star4_V3;
            end;
        elseif p12:get_currency_type() == v_u_3.CurrencyType.Coins then
            if p12:get_currency_amount() <= f_get_productid_getamount(v_u_4.ProductID_Coin1_V3) then
                return v_u_4.ProductID_Coin1_V3;
            elseif p12:get_currency_amount() <= f_get_productid_getamount(v_u_4.ProductID_Coin2_V3) then
                return v_u_4.ProductID_Coin2_V3;
            elseif p12:get_currency_amount() <= f_get_productid_getamount(v_u_4.ProductID_Coin3_V3) then
                return v_u_4.ProductID_Coin3_V3;
            else
                return v_u_4.ProductID_Coin4_V3;
            end;
        else
            return -1;
        end;
    end
}
v_u_15.invalid = function(_) --[[ Name: invalid ]] --[[ Line: 42 ]]
    --[[ Upvalues: (copy 1): v_u_15 ]]
    return v_u_15:new(-1, -1);
end;
v_u_15.show_purchase_redirect = function(_, p_u_16, p17, p_u_18) --[[ Name: show_purchase_redirect ]] --[[ Line: 84 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_15, (copy 3): v_u_1, (copy 4): v_u_7 ]]
    if p17:is_valid() == true then
        local v19 = v_u_15:redirect_to_productid(p17)
        if v19 <= 0 then
            v_u_2:warnf("PurchaseRedirect:show_purchase_redirect(invalid PurchaseRedirect:redirect_to_productid)")
        else
            local v_u_20 = p_u_16._menus:push_menu(v_u_1:new(p_u_16, p_u_16._spui, p_u_16._menus):set_text(p17:title_str(), p17:desc_str()):set_on_close_fn(function() --[[ Line: 100 ]]
                --[[ Upvalues: (copy 1): p_u_18 ]]
                p_u_18(false)
            end))
            p_u_16._player_blob_manager:set_iap_finish_fn(function(_, _, _) --[[ Line: 105 ]]
                --[[ Upvalues: (ref 1): v_u_20, (copy 2): p_u_16, (copy 3): p_u_18 ]]
                v_u_20:set_on_close_fn(nil)
                p_u_16._menus:remove_menu(v_u_20)
                p_u_18(true)
            end)
            if not v_u_7:has_any_paid_item_restrictions() then
                p_u_16._player_blob_manager:prompt_product_purchase(v19)
            end;
        end;
    else
        v_u_2:warnf("PurchaseRedirect:show_purchase_redirect(invalid purchase_redirect)")
        return;
    end;
end;
v_u_15.playerblob_purchase_needs_redirect = function(_, p21, p22, p23) --[[ Name: playerblob_purchase_needs_redirect ]] --[[ Line: 117 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_3, (copy 3): v_u_15 ]]
    v_u_5:is_enum_member(p22, v_u_3.CurrencyType)
    v_u_5:is_int_greater_than(p23, -1)
    if p22 == v_u_3.CurrencyType.Coins then
        local v24 = v_u_3:get_coin_currency(p21)
        if v24 < p23 then
            return v_u_15:new(v_u_3.CurrencyType.Coins, p23 - v24);
        else
            return v_u_15:invalid();
        end;
    elseif p22 == v_u_3.CurrencyType.Stars then
        local v25 = v_u_3:get_star_currency(p21)
        if v25 < p23 then
            return v_u_15:new(v_u_3.CurrencyType.Stars, p23 - v25);
        else
            return v_u_15:invalid();
        end;
    else
        return v_u_15:invalid();
    end;
end;
return v_u_15;
