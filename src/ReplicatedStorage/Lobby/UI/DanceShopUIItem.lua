-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:53 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_4 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.DanceType)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
local v_u_8 = require(game.ReplicatedStorage.Shared.AssertType)
return {
    ["new"] = function(_, p_u_9, p_u_10, p_u_11, p_u_12) --[[ Name: new ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_8, (copy 5): v_u_5, (copy 6): v_u_3, (copy 7): v_u_7, (copy 8): v_u_6 ]]
        local v14 = {
            ["player_blob_updated"] = function(p13) --[[ Name: player_blob_updated ]] --[[ Line: 55 ]]
                p13:render_info()
            end
        }
        local l_Frame_0 = p_u_10.SurfaceGui.Frame
        Vector3.new()
        Vector3.new()
        p_u_10.Parent = p_u_12.Parent
        local v_u_15 = v_u_1:new(p_u_11, p_u_12, p_u_10)
        local v_u_16 = -1
        local v_u_17 = -1
        v14.cons = function(_) --[[ Name: cons ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            v_u_15:layout()
        end;
        v14.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): p_u_11, (ref 3): p_u_12, (ref 4): v_u_15 ]]
            p_u_10:Destroy()
            p_u_10 = nil
            p_u_11 = nil
            p_u_12 = nil
            v_u_15 = nil
        end;
        v14.behaviour_update = function(_, p18, _) --[[ Name: behaviour_update ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_2 ]]
            v_u_15:set_scale(v_u_2:expt_sec(v_u_15:get_scale(), 1, 1, p18))
        end;
        v14.visual_update = function(_, _, _) --[[ Name: visual_update ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            v_u_15:layout()
        end;
        v14.set_visible = function(_, p19) --[[ Name: set_visible ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): p_u_10 ]]
            p_u_10.SurfaceGui.Enabled = p19
        end;
        v14.render_info = function(p20) --[[ Name: render_info ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (copy 3): l_Frame_0 ]]
            if v_u_16 == -1 or v_u_17 == -1 then
                return;
            elseif p20:can_purchase() then
                l_Frame_0.PriceSection.Visible = true
                l_Frame_0.BoughtDisplay.Visible = false
                l_Frame_0.ItemDisplay.Icon.Visible = true
            else
                l_Frame_0.PriceSection.Visible = false
                l_Frame_0.BoughtDisplay.Visible = true
                l_Frame_0.ItemDisplay.Icon.Visible = false
            end;
        end;
        v14.can_purchase = function(_) --[[ Name: can_purchase ]] --[[ Line: 75 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_4, (ref 3): v_u_16 ]]
            return v_u_4:get_owned_danceid_to_equipped_dict((p_u_9._player_blob_manager:get_player_blob())):contains(v_u_16) ~= true;
        end;
        v14.set_item_info = function(p21, p22) --[[ Name: set_item_info ]] --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_8, (ref 4): v_u_5, (copy 5): l_Frame_0, (ref 6): v_u_3, (ref 7): v_u_7, (ref 8): v_u_6, (ref 9): v_u_15 ]]
            if p22 ~= nil then
                v_u_16 = p22.DanceId
                v_u_17 = p22.SaleId
                v_u_8:is_int_greater_than(v_u_17, 0)
                v_u_8:is_true(v_u_5:singleton():contains_dance_for_id(v_u_16))
                p21:render_info()
                l_Frame_0.PriceSection.Icon.Image = v_u_3:currency_type_get_image(p22.PriceType)
                l_Frame_0.PriceSection.Display.Text = string.format("%d", p22.PriceValue)
                l_Frame_0.ItemDisplay.NameDisplay.Text = string.format("[%d] %s", v_u_16, v_u_5:singleton():get_dance_name_for_id(v_u_16))
                l_Frame_0.ItemDisplay.NameDisplay.TextColor3 = v_u_7:rarity_to_color(v_u_5:singleton():get_dance_rarity_for_id(v_u_16))
                l_Frame_0.ItemDisplay.SubDisplay.Text = v_u_6:type_to_string(v_u_5:singleton():get_dance_type_for_id(v_u_16))
                l_Frame_0.ItemDisplay.Icon.Image = v_u_5:singleton():get_dance_icon_for_id(v_u_16)
                v_u_15:set_scale(1.15)
            end;
        end;
        v14:cons()
        return v14;
    end
};
