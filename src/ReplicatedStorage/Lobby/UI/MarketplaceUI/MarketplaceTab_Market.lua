-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:55 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_9 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.MarketplaceUI.MarketplaceTab)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.MarketplaceUtils)
require(game.ReplicatedStorage.PlayerInfo.MarketplaceSale)
local v_u_12 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_14 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v15 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_16 = nil
local v_u_17 = nil
v15:require_client(function() --[[ Line: 26 ]]
    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17 ]]
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.MarketplaceUI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.UI.CraftingUISearchSection)
end)
local v_u_18 = {
    ["Mode"] = {
        ["Loading"] = 0,
        ["Loaded"] = 1
    },
    ["SortMode"] = {
        ["ByType"] = 1,
        ["ByPrice"] = 2,
        ["BySeller"] = 3
    }
}
local v_u_41 = {
    ["new"] = function(_, p_u_19, p_u_20, p_u_21, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 449 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_6, (copy 4): v_u_12, (copy 5): v_u_1 ]]
        local v25 = {
            ["layout"] = function(_) end,
            ["behaviour_update"] = function(_, _) end
        }
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = nil
        local v_u_29 = nil
        local v_u_30 = nil
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 462 ]]
            --[[ Upvalues: (ref 1): v_u_26, (copy 2): p_u_23, (copy 3): p_u_24, (copy 4): p_u_22, (ref 5): v_u_27, (copy 6): p_u_20, (copy 7): p_u_19, (ref 8): v_u_4, (ref 9): v_u_3, (ref 10): v_u_6, (ref 11): v_u_30, (copy 12): p_u_21, (ref 13): v_u_29, (ref 14): v_u_28, (ref 15): v_u_31, (ref 16): v_u_32, (ref 17): v_u_33, (ref 18): v_u_34, (ref 19): v_u_35, (ref 20): v_u_36, (ref 21): v_u_37 ]]
            v_u_26 = p_u_23:Clone()
            v_u_26:SetPrimaryPartCFrame(p_u_24.CFrame)
            v_u_26.Parent = p_u_22
            v_u_27 = p_u_20:add_cycle_element(p_u_19, 1, v_u_4:new(v_u_3:new(p_u_20, p_u_22.PrimaryPart, v_u_26.PrimaryPart), p_u_19._spui, function() --[[ Line: 469 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_6, (ref 3): v_u_30, (ref 4): p_u_21 ]]
                p_u_19._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                if v_u_30 ~= nil then
                    p_u_21:select_sale(v_u_30)
                end;
            end)):set_selected_rotation_amplitude(0):set_triggered_scale_offset(0.15):set_selected_tar_scale(1.05):set_auto_zoffset_behaviour(true)
            v_u_29 = v_u_26.MainSurface.SurfaceGui
            v_u_28 = v_u_29.Frame
            v_u_31 = v_u_28.IconSection.Icon
            v_u_32 = v_u_28.CountDisplay.Display
            v_u_33 = v_u_28.NameDisplay
            v_u_34 = v_u_28.CoinSection.Display
            v_u_35 = v_u_28.EachDisplay
            v_u_36 = v_u_28.SoldByDisplay
            v_u_37 = v_u_28.PlayerIconDisplay
        end;
        v25.update_from_sale = function(_, p38) --[[ Name: update_from_sale ]] --[[ Line: 493 ]]
            --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_31, (ref 3): v_u_12, (ref 4): v_u_32, (ref 5): v_u_33, (ref 6): v_u_34, (ref 7): v_u_1, (ref 8): v_u_35, (ref 9): v_u_36, (ref 10): v_u_37 ]]
            v_u_30 = p38
            if v_u_30 ~= nil then
                v_u_31.Image = v_u_12:singleton():get_material_icon(p38:get_materialid())
                v_u_32.Text = tostring(p38:get_count())
                v_u_33.Text = v_u_12:singleton():get_material_name(p38:get_materialid())
                v_u_33.TextColor3 = v_u_12:singleton():tier_get_color(v_u_12:singleton():get_material_tier(p38:get_materialid()))
                v_u_34.Text = v_u_1:comma_value(p38:get_price())
                v_u_35.Text = string.format("(%s Each)", v_u_1:comma_value((math.floor(p38:get_price() / p38:get_count()))))
                v_u_36.Text = p38:get_seller_name()
                v_u_37.Image = v_u_1:transparent_assetid()
                v_u_1:get_user_thumbnail(p38:get_seller_id(), function(p39, _) --[[ Line: 506 ]]
                    --[[ Upvalues: (ref 1): v_u_37 ]]
                    v_u_37.Image = p39
                end, false)
            end;
        end;
        v25.set_visible = function(_, p40) --[[ Name: set_visible ]] --[[ Line: 512 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            v_u_27:set_visible(p40)
        end;
        f_cons()
        return v25;
    end
}
local function _() --[[ Name: all_sort_modes ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_18 ]]
    return v_u_2:new({ v_u_18.SortMode.ByType, v_u_18.SortMode.ByPrice, v_u_18.SortMode.BySeller });
end;
local function _(p42) --[[ Name: sort_mode_to_text ]] --[[ Line: 52 ]]
    --[[ Upvalues: (copy 1): v_u_18 ]]
    return p42 == v_u_18.SortMode.ByType and "Type" or (p42 == v_u_18.SortMode.ByPrice and "Price" or "Seller");
end;
local l_ByType_0 = v_u_18.SortMode.ByType
local v_u_43 = true
v_u_18.new = function(_, p_u_44, p_u_45, p_u_46, p_u_47, p_u_48) --[[ Name: new ]] --[[ Line: 66 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_18, (copy 3): v_u_2, (copy 4): v_u_9, (copy 5): v_u_4, (copy 6): v_u_3, (copy 7): v_u_6, (copy 8): v_u_41, (ref 9): l_ByType_0, (ref 10): v_u_43, (copy 11): v_u_11, (copy 12): v_u_14, (copy 13): v_u_1, (ref 14): v_u_16, (copy 15): v_u_5, (ref 16): v_u_17, (copy 17): v_u_12, (copy 18): v_u_13, (copy 19): v_u_8, (copy 20): v_u_7 ]]
    local v_u_49 = v_u_10:new()
    v_u_49.get_tab = function(_) --[[ Name: get_tab ]] --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        return v_u_10.Tab.Market;
    end;
    local v_u_50 = nil
    local v_u_51 = nil
    local v_u_52 = nil
    local v_u_53 = nil
    local v_u_54 = nil
    local v_u_55 = nil
    local v_u_56 = nil
    local v_u_57 = nil
    local v_u_58 = nil
    local v_u_59 = nil
    local v_u_60 = nil
    local v_u_61 = nil
    local v_u_62 = nil
    local v_u_63 = nil
    local v_u_64 = nil
    local l_Loading_0 = v_u_18.Mode.Loading
    local v_u_65 = v_u_2:new()
    local v_u_66 = v_u_2:new()
    local v_u_67 = 0
    local v_u_68 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 88 ]]
        --[[ Upvalues: (ref 1): v_u_50, (copy 2): p_u_48, (ref 3): v_u_9, (ref 4): v_u_54, (ref 5): v_u_55, (ref 6): v_u_56, (ref 7): v_u_57, (ref 8): v_u_58, (ref 9): v_u_59, (ref 10): v_u_60, (ref 11): v_u_61, (ref 12): v_u_62, (ref 13): v_u_63, (ref 14): v_u_64, (copy 15): v_u_66, (copy 16): v_u_65, (ref 17): v_u_51, (copy 18): p_u_47, (copy 19): p_u_44, (ref 20): v_u_4, (ref 21): v_u_3, (copy 22): p_u_45, (ref 23): v_u_6, (ref 24): v_u_67, (copy 25): v_u_49, (ref 26): v_u_52, (ref 27): v_u_53 ]]
        v_u_50 = p_u_48.MainSurface.SurfaceGui.Frame.LoadedFrame.MarketplaceSection
        v_u_9:is_non_nil(v_u_50)
        v_u_54 = v_u_50.SelectedItemSection.IconFrame.Icon
        v_u_55 = v_u_50.SelectedItemSection.CountDisplay.Display
        v_u_56 = v_u_50.SelectedItemSection.CountDisplay
        v_u_57 = v_u_50.SelectedItemSection.CoinSection.Display
        v_u_58 = v_u_50.SelectedItemSection.EachDisplay
        v_u_59 = v_u_50.SelectedItemSection.NameDisplay
        v_u_60 = v_u_50.SelectedItemSection.DescriptionDisplay
        v_u_61 = v_u_50.SelectedItemSection.PlayerIconDisplay
        v_u_62 = v_u_50.SelectedItemSection.SoldByDisplay
        v_u_63 = v_u_50.PageDisplay
        v_u_64 = v_u_50.LoadingDisplay
        local function _() --[[ Name: get_max_page_offset ]] --[[ Line: 104 ]]
            --[[ Upvalues: (ref 1): v_u_66, (ref 2): v_u_65 ]]
            return v_u_66:count() == 0 and 0 or math.floor(math.max(v_u_65:count() - 1, 0) / v_u_66:count());
        end;
        v_u_51 = p_u_47:add_cycle_element(p_u_44, 1, v_u_4:new(v_u_3:new(p_u_47, p_u_48.PrimaryPart, p_u_48.MarketplaceElements.TopArrowSurface), p_u_45, function() --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_6, (ref 3): v_u_67, (ref 4): v_u_66, (ref 5): v_u_65, (ref 6): v_u_49 ]]
            p_u_44._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_67 = v_u_67 - 1
            if v_u_67 < 0 then
                v_u_67 = v_u_66:count() == 0 and 0 or math.floor(math.max(v_u_65:count() - 1, 0) / v_u_66:count())
            end;
            v_u_49:refresh_state()
        end))
        v_u_52 = p_u_47:add_cycle_element(p_u_44, 1, v_u_4:new(v_u_3:new(p_u_47, p_u_48.PrimaryPart, p_u_48.MarketplaceElements.BottomArrowSurface), p_u_45, function() --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_6, (ref 3): v_u_67, (ref 4): v_u_66, (ref 5): v_u_65, (ref 6): v_u_49 ]]
            p_u_44._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_67 = v_u_67 + 1
            if v_u_67 > (v_u_66:count() == 0 and 0 or math.floor(math.max(v_u_65:count() - 1, 0) / v_u_66:count())) then
                v_u_67 = 0
            end;
            v_u_49:refresh_state()
        end))
        v_u_53 = p_u_47:add_cycle_element(p_u_44, 1, v_u_4:new(v_u_3:new(p_u_47, p_u_48.PrimaryPart, p_u_48.MarketplaceElements.BuyButtonSurface), p_u_45, function() --[[ Line: 138 ]]
            --[[ Upvalues: (ref 1): p_u_44, (ref 2): v_u_6, (ref 3): v_u_49 ]]
            p_u_44._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_49:buy_selected_sale()
        end):set_passive_anim(true))
        v_u_49:init_list_element_protos()
        v_u_49:set_visible(false)
    end;
    v_u_49.init_list_element_protos = function(p69) --[[ Name: init_list_element_protos ]] --[[ Line: 148 ]]
        --[[ Upvalues: (copy 1): p_u_48, (ref 2): v_u_2, (copy 3): v_u_66, (ref 4): v_u_41, (copy 5): p_u_44, (copy 6): p_u_47 ]]
        local l_SaleElementProto_0 = p_u_48.MarketplaceElements.SaleElementProto
        l_SaleElementProto_0.Parent = nil
        local v70 = v_u_2:new():push_back_table_list({
            p_u_48.MarketplaceElements.Anchors.Anchor1,
            p_u_48.MarketplaceElements.Anchors.Anchor2,
            p_u_48.MarketplaceElements.Anchors.Anchor3,
            p_u_48.MarketplaceElements.Anchors.Anchor4,
            p_u_48.MarketplaceElements.Anchors.Anchor5,
            p_u_48.MarketplaceElements.Anchors.Anchor6,
            p_u_48.MarketplaceElements.Anchors.Anchor7,
            p_u_48.MarketplaceElements.Anchors.Anchor8
        })
        for v71 = 1, v70:count() do
            local v72 = v70:get(v71)
            v72.Parent = nil
            v_u_66:push_back(v_u_41:new(p_u_44, p_u_47, p69, p_u_48, l_SaleElementProto_0, v72))
        end;
    end;
    v_u_49.sort_buttons_update_mode = function(_) --[[ Name: sort_buttons_update_mode ]] --[[ Line: 168 ]]
        --[[ Upvalues: (copy 1): p_u_47, (ref 2): l_Loading_0, (ref 3): v_u_18, (ref 4): v_u_2, (ref 5): l_ByType_0, (ref 6): v_u_43, (ref 7): v_u_4 ]]
        local v73, v74 = p_u_47:get_sort_section_and_buttons()
        if l_Loading_0 == v_u_18.Mode.Loaded then
            v73.Visible = true
            local v75 = v_u_2:new({ v_u_18.SortMode.ByType, v_u_18.SortMode.ByPrice, v_u_18.SortMode.BySeller })
            for v76 = 1, v74:count() do
                local v77 = v74:get(v76)
                if v76 <= v75:count() then
                    v77:set_visible(true)
                    local v78 = v77:get_bound_data()
                    local v79 = v75:get(v76)
                    local v80 = v79 == v_u_18.SortMode.ByType and "Type" or (v79 == v_u_18.SortMode.ByPrice and "Price" or "Seller")
                    if v76 == l_ByType_0 then
                        v_u_4:set_button_text(v77, string.format("%s %s", v80, v_u_43 == true and "\226\134\147" or "\226\134\145"))
                        v78:set_toggle(true)
                    else
                        v_u_4:set_button_text(v77, v80)
                        v78:set_toggle(false)
                    end;
                else
                    v77:set_visible(false)
                end;
            end;
        else
            v73.Visible = false
            for v81 = 1, v74:count() do
                v74:get(v81):set_visible(false)
            end;
        end;
    end;
    v_u_49.on_sort_button_index_pressed = function(p82, p83) --[[ Name: on_sort_button_index_pressed ]] --[[ Line: 203 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_18, (ref 3): l_ByType_0, (ref 4): v_u_43 ]]
        v_u_9:is_enum_member(p83, v_u_18.SortMode)
        if l_ByType_0 == p83 then
            v_u_43 = not v_u_43
        else
            v_u_43 = true
        end;
        l_ByType_0 = p83
        p82:reset()
        p82:refresh_state()
    end;
    v_u_49.request_sale_data = function(_, p_u_84) --[[ Name: request_sale_data ]] --[[ Line: 215 ]]
        --[[ Upvalues: (copy 1): p_u_44, (copy 2): v_u_65, (ref 3): v_u_11, (ref 4): v_u_14, (ref 5): v_u_1 ]]
        p_u_44._shop_local_protocol:marketplace_query_sales(function(p85) --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): v_u_65, (ref 2): v_u_11, (ref 3): v_u_14, (ref 4): v_u_1, (copy 5): p_u_84 ]]
            v_u_65:clear()
            local v86 = v_u_11:sales_table_to_list(p85)
            for v87 = 1, v86:count() do
                local v88 = v86:get(v87)
                if v_u_14.DebugMarketplaceShowOwnSale == true then
                    v_u_65:push_back(v88)
                elseif v88:get_seller_id() ~= v_u_1:get_local_userid() then
                    v_u_65:push_back(v88)
                end;
            end;
            p_u_84()
        end)
    end;
    v_u_49.layout = function(_) --[[ Name: layout ]] --[[ Line: 235 ]]
        --[[ Upvalues: (copy 1): v_u_66 ]]
        for v89 = 1, v_u_66:count() do
            v_u_66:get(v89):layout()
        end;
    end;
    v_u_49.behaviour_update = function(_, p90) --[[ Name: behaviour_update ]] --[[ Line: 241 ]]
        --[[ Upvalues: (copy 1): v_u_66 ]]
        for v91 = 1, v_u_66:count() do
            v_u_66:get(v91):behaviour_update(p90)
        end;
    end;
    v_u_49.reset = function(p_u_92) --[[ Name: reset ]] --[[ Line: 247 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_18, (ref 3): v_u_67, (ref 4): v_u_68, (copy 5): p_u_47, (ref 6): v_u_10, (ref 7): v_u_16, (ref 8): v_u_1, (ref 9): v_u_5 ]]
        l_Loading_0 = v_u_18.Mode.Loading
        v_u_67 = 0
        v_u_68 = nil
        p_u_92:sort_buttons_update_mode()
        p_u_92:request_sale_data(function() --[[ Line: 253 ]]
            --[[ Upvalues: (ref 1): p_u_47, (ref 2): v_u_10, (ref 3): v_u_16, (ref 4): v_u_1, (ref 5): v_u_5, (ref 6): l_Loading_0, (ref 7): v_u_18, (copy 8): p_u_92 ]]
            if p_u_47 == nil or (p_u_47:get_selected_tab() ~= v_u_10.Tab.Market or p_u_47:get_current_mode() == v_u_16.Mode.Kill) then
                if v_u_1:is_dev_build() then
                    v_u_5:warnf("MarketplaceTab_Market:reset() _marketplace_ui:get_selected_tab(%s) _marketplace_ui:get_current_mode(%s)", tostring(p_u_47:get_selected_tab()), (tostring(p_u_47:get_current_mode())))
                end;
            else
                l_Loading_0 = v_u_18.Mode.Loaded
                p_u_92:refresh_state()
                p_u_92:sort_buttons_update_mode()
            end;
        end)
    end;
    local v_u_93 = false
    v_u_49.set_visible = function(p94, p95) --[[ Name: set_visible ]] --[[ Line: 267 ]]
        --[[ Upvalues: (ref 1): v_u_93 ]]
        if v_u_93 ~= true and p95 == true then
            p94:reset()
        end;
        v_u_93 = p95
        p94:refresh_state()
    end;
    v_u_49.select_sale = function(p96, p97) --[[ Name: select_sale ]] --[[ Line: 275 ]]
        --[[ Upvalues: (ref 1): v_u_68 ]]
        v_u_68 = p97
        p96:refresh_state()
    end;
    v_u_49.refresh_state = function(_) --[[ Name: refresh_state ]] --[[ Line: 280 ]]
        --[[ Upvalues: (copy 1): p_u_47, (ref 2): v_u_93, (ref 3): v_u_50, (ref 4): l_Loading_0, (ref 5): v_u_18, (ref 6): v_u_62, (ref 7): v_u_56, (ref 8): v_u_61, (ref 9): v_u_1, (ref 10): v_u_60, (ref 11): v_u_59, (ref 12): v_u_58, (ref 13): v_u_57, (ref 14): v_u_54, (ref 15): v_u_63, (ref 16): v_u_64, (copy 17): v_u_66, (ref 18): v_u_43, (copy 19): v_u_65, (ref 20): l_ByType_0, (ref 21): v_u_17, (ref 22): v_u_67, (ref 23): v_u_51, (ref 24): v_u_52, (ref 25): v_u_68, (ref 26): v_u_55, (ref 27): v_u_53, (ref 28): v_u_12, (copy 29): p_u_44, (ref 30): v_u_13 ]]
        p_u_47:get_empty_display().Visible = false
        if v_u_93 == true then
            v_u_50.Visible = true
            if l_Loading_0 == v_u_18.Mode.Loading then
                v_u_62.Text = "-"
                v_u_56.Visible = false
                v_u_61.Image = v_u_1:transparent_assetid()
                v_u_60.Text = "Loading..."
                v_u_59.Text = ""
                v_u_58.Text = ""
                v_u_57.Text = "-"
                v_u_54.Image = v_u_1:transparent_assetid()
                v_u_63.Text = "Loading..."
                v_u_64.Visible = true
                for v98 = 1, v_u_66:count() do
                    v_u_66:get(v98):set_visible(false)
                end;
                return;
            end;
            if l_Loading_0 == v_u_18.Mode.Loaded then
                local function f_sort_by_price(p99, p100) --[[ Name: sort_by_price ]] --[[ Line: 301 ]]
                    --[[ Upvalues: (ref 1): v_u_43 ]]
                    local v101
                    if v_u_43 then
                        v101 = p100:get_price() - p99:get_price()
                    else
                        v101 = p99:get_price() - p100:get_price()
                    end;
                    if v101 == 0 then
                        if v_u_43 then
                            v101 = p100:get_seller_id() - p99:get_seller_id()
                        else
                            v101 = p99:get_seller_id() - p100:get_seller_id()
                        end;
                        if v101 == 0 then
                            if v_u_43 then
                                return p100:get_index() - p99:get_index();
                            end;
                            v101 = p99:get_index() - p100:get_index()
                        end;
                    end;
                    return v101;
                end;
                v_u_65:sort(function(p102, p103) --[[ Line: 325 ]]
                    --[[ Upvalues: (ref 1): l_ByType_0, (ref 2): v_u_18, (ref 3): v_u_43, (ref 4): v_u_17, (copy 5): f_sort_by_price ]]
                    if l_ByType_0 == v_u_18.SortMode.ByType then
                        local v104
                        if v_u_43 then
                            v104 = v_u_17:materialid_get_type_sort_value(p103:get_materialid()) - v_u_17:materialid_get_type_sort_value(p102:get_materialid())
                        else
                            v104 = v_u_17:materialid_get_type_sort_value(p102:get_materialid()) - v_u_17:materialid_get_type_sort_value(p103:get_materialid())
                        end;
                        if v104 == 0 then
                            return f_sort_by_price(p102, p103);
                        else
                            return v104;
                        end;
                    else
                        if l_ByType_0 == v_u_18.SortMode.ByPrice then
                            return f_sort_by_price(p102, p103);
                        end;
                        if p102:get_seller_name() == p103:get_seller_name() then
                            return f_sort_by_price(p102, p103);
                        end;
                        local v105 = p103:get_seller_name() > p102:get_seller_name() == false and -1 or 1
                        if v_u_43 ~= true then
                            v105 = -v105
                        end;
                        return v105;
                    end;
                end)
                for v106 = 1, v_u_66:count() do
                    local v107 = v_u_67 * v_u_66:count() + v106
                    if v107 <= v_u_65:count() then
                        v_u_66:get(v106):update_from_sale((v_u_65:get(v107)))
                        v_u_66:get(v106):set_visible(true)
                    else
                        v_u_66:get(v106):set_visible(false)
                    end;
                end;
                if v_u_65:count() == 0 then
                    p_u_47:get_empty_display().Visible = true
                    p_u_47:get_empty_display().Text = "No available marketplace sales in this server."
                end;
                v_u_64.Visible = false
                v_u_63.Text = string.format("Page %d (of %d)", v_u_67 + 1, (math.max(1, (math.ceil(v_u_65:count() / v_u_66:count())))))
                v_u_51:set_visible(true)
                v_u_52:set_visible(true)
                if v_u_68 == nil then
                    v_u_62.Text = "-"
                    v_u_56.Visible = false
                    v_u_55.Text = ""
                    v_u_61.Image = v_u_1:transparent_assetid()
                    v_u_60.Text = "Select a sale to view more info..."
                    v_u_59.Text = ""
                    v_u_58.Text = ""
                    v_u_57.Text = "-"
                    v_u_54.Image = v_u_1:transparent_assetid()
                    v_u_53:set_visible(false)
                else
                    v_u_62.Text = v_u_68:get_seller_name()
                    v_u_56.Visible = true
                    v_u_55.Text = tostring(v_u_68:get_count())
                    v_u_61.Image = v_u_1:transparent_assetid()
                    v_u_1:get_user_thumbnail(v_u_68:get_seller_id(), function(p108, _) --[[ Line: 389 ]]
                        --[[ Upvalues: (ref 1): v_u_61 ]]
                        v_u_61.Image = p108
                    end, false)
                    v_u_60.Text = v_u_12:singleton():get_material_description(v_u_68:get_materialid())
                    v_u_59.Text = v_u_12:singleton():get_material_name(v_u_68:get_materialid())
                    v_u_59.TextColor3 = v_u_12:singleton():tier_get_color(v_u_12:singleton():get_material_tier(v_u_68:get_materialid()))
                    v_u_58.Text = string.format("(%s Each)", v_u_1:comma_value((math.floor(v_u_68:get_price() / v_u_68:get_count()))))
                    v_u_57.Text = v_u_1:comma_value(v_u_68:get_price())
                    v_u_54.Image = v_u_12:singleton():get_material_icon(v_u_68:get_materialid())
                    v_u_53:set_visible(v_u_13:get_coin_currency((p_u_44._player_blob_manager:get_player_blob())) >= v_u_68:get_price())
                end;
            end;
        else
            v_u_50.Visible = false
            v_u_51:set_visible(false)
            v_u_52:set_visible(false)
            v_u_53:set_visible(false)
            for v109 = 1, v_u_66:count() do
                v_u_66:get(v109):set_visible(false)
            end;
        end;
    end;
    v_u_49.buy_selected_sale = function(p_u_110) --[[ Name: buy_selected_sale ]] --[[ Line: 415 ]]
        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_68, (copy 3): p_u_46, (ref 4): v_u_8, (copy 5): p_u_44, (copy 6): p_u_45, (ref 7): v_u_7, (ref 8): v_u_6, (ref 9): v_u_12 ]]
        v_u_9:is_non_nil(v_u_68)
        local v_u_111 = v_u_68
        local v_u_112 = p_u_46:push_menu(v_u_8:new(p_u_44, p_u_45, p_u_46):set_text("Buying Sale", "Please wait..."):set_close_button_visible(false))
        p_u_44._evt:wait_on_event_once(v_u_7.EVT_Marketplace_ServerPurchaseSaleResponse, function(p113, p114) --[[ Line: 420 ]]
            --[[ Upvalues: (ref 1): p_u_46, (copy 2): v_u_112, (ref 3): v_u_8, (ref 4): p_u_44, (ref 5): p_u_45, (copy 6): p_u_110, (ref 7): v_u_6, (copy 8): v_u_111, (ref 9): v_u_12 ]]
            if p113 == true then
                p_u_44._player_blob_manager:do_sync(function() --[[ Line: 428 ]]
                    --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_112, (ref 3): p_u_44, (ref 4): v_u_6, (ref 5): v_u_8, (ref 6): p_u_45, (ref 7): v_u_111, (ref 8): v_u_12, (ref 9): p_u_110 ]]
                    p_u_46:remove_menu(v_u_112)
                    p_u_44._sfx_manager:play_sfx(v_u_6.SFX_ACQUIRE)
                    p_u_46:push_menu(v_u_8:new(p_u_44, p_u_45, p_u_46):set_text("Bought!", string.format("Bought %s\'s sale of %d %s(s) for %d Coins!", v_u_111:get_seller_name(), v_u_111:get_count(), v_u_12:singleton():get_material_name(v_u_111:get_materialid()), v_u_111:get_price())))
                    p_u_110:reset()
                    p_u_110:refresh_state()
                end)
            else
                p_u_46:remove_menu(v_u_112)
                p_u_46:push_menu(v_u_8:new(p_u_44, p_u_45, p_u_46):set_text("Error", p114))
                p_u_110:reset()
                p_u_110:refresh_state()
            end;
        end)
        p_u_44._evt:fire_event_to_server(v_u_7.EVT_Marketplace_ClientPurchaseSale, v_u_68:get_seller_id(), v_u_68:get_index())
    end;
    f_cons()
    return v_u_49;
end;
return v_u_18;
