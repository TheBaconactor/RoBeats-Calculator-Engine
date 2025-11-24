-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:51 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_3 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.LocalShared.ShopLocalProtocol)
require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_6 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2GearStatDisplay)
local v_u_7 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_8 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_9 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.MaterialsRequiredDisplay)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_12 = {
    ["Mode"] = {
        ["Hidden"] = 1
    }
}
v_u_12.new = function(_, p_u_13, p_u_14, p_u_15, p_u_16) --[[ Name: new ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_12, (copy 3): v_u_1, (copy 4): v_u_6, (copy 5): v_u_10, (copy 6): v_u_4, (copy 7): v_u_8, (copy 8): v_u_9, (copy 9): v_u_3, (copy 10): v_u_7, (copy 11): v_u_11, (copy 12): v_u_5 ]]
    local v18 = {
        ["player_blob_updated"] = function(p17) --[[ Name: player_blob_updated ]] --[[ Line: 89 ]]
            p17:render_info()
        end
    }
    local l_Frame_0 = p_u_14.SurfaceGui.Frame
    Vector3.new()
    Vector3.new()
    p_u_14.Parent = p_u_16.Parent
    local v_u_19 = v_u_2:new(p_u_15, p_u_16, p_u_14)
    local v_u_20 = -1
    local v_u_21 = -1
    local v_u_22 = nil
    local v_u_23 = -1
    local v_u_24 = nil
    local v_u_25 = nil
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = v_u_1:new()
    local v_u_29 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_6, (copy 3): l_Frame_0, (ref 4): v_u_24, (ref 5): v_u_25, (ref 6): v_u_26, (ref 7): v_u_29, (copy 8): v_u_28, (ref 9): v_u_10, (ref 10): v_u_27, (ref 11): v_u_19 ]]
        v_u_22 = v_u_6:new(nil, l_Frame_0.ItemDisplay)
        v_u_24 = l_Frame_0.BlueprintDisplay.MaterialNameDisplay
        v_u_25 = l_Frame_0.BlueprintDisplay.MaterialDescriptionDisplay
        v_u_26 = l_Frame_0.BlueprintDisplay.IconSection.MaterialIcon
        v_u_29 = l_Frame_0.CollectionOwnedDisplay
        v_u_29.Visible = false
        v_u_28:push_back(v_u_10:new(l_Frame_0.BlueprintDisplay.RequirementDisplay1))
        v_u_28:push_back(v_u_10:new(l_Frame_0.BlueprintDisplay.RequirementDisplay2))
        v_u_28:push_back(v_u_10:new(l_Frame_0.BlueprintDisplay.RequirementDisplay3))
        v_u_28:push_back(v_u_10:new(l_Frame_0.BlueprintDisplay.RequirementDisplay4))
        v_u_27 = v_u_6:new(nil, l_Frame_0.BlueprintDisplay)
        v_u_27:set_hidden()
        v_u_19:layout()
    end;
    v18.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 69 ]]
        --[[ Upvalues: (ref 1): p_u_14, (ref 2): p_u_15, (ref 3): p_u_16, (ref 4): v_u_19 ]]
        p_u_14:Destroy()
        p_u_14 = nil
        p_u_15 = nil
        p_u_16 = nil
        v_u_19 = nil
    end;
    v18.behaviour_update = function(_, p30, _) --[[ Name: behaviour_update ]] --[[ Line: 77 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_4 ]]
        v_u_19:set_scale(v_u_4:expt_sec(v_u_19:get_scale(), 1, 1, p30))
    end;
    v18.visual_update = function(_, p31, p32) --[[ Name: visual_update ]] --[[ Line: 81 ]]
        --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_22, (ref 3): v_u_27 ]]
        v_u_19:layout()
        v_u_22:visual_update(p31, p32)
        v_u_27:visual_update(p31, p32)
    end;
    v18.set_visible = function(_, p33) --[[ Name: set_visible ]] --[[ Line: 87 ]]
        --[[ Upvalues: (ref 1): p_u_14 ]]
        p_u_14.SurfaceGui.Enabled = p33
    end;
    v18.render_info = function(p_u_34) --[[ Name: render_info ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): v_u_20, (copy 2): l_Frame_0, (copy 3): p_u_13, (ref 4): v_u_8, (ref 5): v_u_23, (copy 6): v_u_28, (ref 7): v_u_24, (ref 8): v_u_25, (ref 9): v_u_26, (ref 10): v_u_9, (ref 11): v_u_22, (ref 12): v_u_27, (ref 13): v_u_3, (ref 14): v_u_7, (ref 15): v_u_29, (ref 16): v_u_11 ]]
        if v_u_20 ~= -1 then
            pcall(function() --[[ Line: 98 ]]
                --[[ Upvalues: (copy 1): p_u_34, (ref 2): l_Frame_0, (ref 3): p_u_13, (ref 4): v_u_8, (ref 5): v_u_23, (ref 6): v_u_28, (ref 7): v_u_24, (ref 8): v_u_25, (ref 9): v_u_26, (ref 10): v_u_9, (ref 11): v_u_22, (ref 12): v_u_27, (ref 13): v_u_3, (ref 14): v_u_20, (ref 15): v_u_7, (ref 16): v_u_29, (ref 17): v_u_11 ]]
                if not p_u_34:can_purchase() then
                    l_Frame_0.PriceSection.Visible = false
                    l_Frame_0.BoughtDisplay.Visible = true
                    v_u_29.Visible = false
                    v_u_22:set_hidden()
                    v_u_27:set_hidden()
                    return;
                end;
                l_Frame_0.PriceSection.Visible = true
                l_Frame_0.BoughtDisplay.Visible = false
                local v35 = p_u_13._player_blob_manager:get_player_blob()
                local v36 = false
                local v37 = -1
                if v_u_8:singleton():contains_material(v_u_23) then
                    for v38 = 1, v_u_28:count() do
                        v_u_28:get(v38):set_visible(false)
                    end;
                    v_u_24.Text = v_u_8:singleton():get_material_name(v_u_23)
                    v_u_24.TextColor3 = v_u_8:singleton():tier_get_color(v_u_8:singleton():get_material_tier(v_u_23))
                    v_u_25.Text = v_u_8:singleton():get_material_description(v_u_23)
                    v_u_26.Image = v_u_8:singleton():get_material_icon(v_u_23)
                    for v39, v40 in v_u_8:singleton():gear_recipe_key_itr() do
                        local _, v41 = v40:has_display_requirement_materialid()
                        if v41 == v_u_23 then
                            local v42 = v_u_8:singleton():get_gear_recipe_requirements_dict(v39)
                            local v43 = v42:key_list()
                            for v44 = 1, v_u_28:count() do
                                if v43:count() < v44 then
                                    break;
                                end;
                                local v45 = v43:get(v44)
                                local v46 = v_u_28:get(v44)
                                v46:set_visible(true)
                                v46:set_info(v_u_8:singleton():get_material_name(v45), v_u_8:singleton():get_material_icon(v45), v_u_8:singleton():tier_get_color(v_u_8:singleton():get_material_tier(v45)), v_u_9:get_count_of_material(v35, v45), v42:get(v45))
                            end;
                            v_u_22:set_hidden()
                            v_u_27:set_equipment_id(v40:get_gear_id())
                            v37 = v40:get_gear_id()
                            v36 = true
                            break;
                        end;
                    end;
                    if v36 ~= true then
                        v_u_3:warnf("GearShopUIItem _material_id(%s) but no gear_recipe found", (tostring(v_u_23)))
                    end;
                end;
                if v36 ~= true then
                    v_u_22:set_equipment_id(v_u_20)
                    v37 = v_u_20
                    v_u_27:set_hidden()
                end;
                if v_u_7:singleton():get_equipment_for_id(v37) then
                    v_u_29.Visible = v_u_11:get_playerblob_equipmentid_in_collection(v35, v37, p_u_13._player_blob_manager:get_cached_collection_info())
                else
                    v_u_29.Visible = false
                end;
            end)
        end;
    end;
    v18.can_purchase = function(_) --[[ Name: can_purchase ]] --[[ Line: 172 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_5, (ref 3): v_u_21 ]]
        return v_u_5:get_count_for_gear_shop_saleid(p_u_13._player_blob_manager:get_player_blob(), v_u_21) == 0;
    end;
    v18.set_item_info = function(p47, p48) --[[ Name: set_item_info ]] --[[ Line: 177 ]]
        --[[ Upvalues: (copy 1): l_Frame_0, (ref 2): v_u_20, (ref 3): v_u_21, (ref 4): v_u_23, (ref 5): v_u_5, (ref 6): v_u_19 ]]
        if p48 ~= nil then
            local v49 = l_Frame_0
            v_u_20 = p48.EquipmentID
            v_u_21 = p48.SaleId
            v_u_23 = p48.MaterialID
            p47:render_info()
            v_u_5:currency_type_render_icon(p48.PriceType, v49.PriceSection.Icon)
            v49.PriceSection.Display.Text = string.format("%d", p48.PriceValue)
            v_u_19:set_scale(1.15)
        end;
    end;
    f_cons()
    return v18;
end;
return v_u_12;
