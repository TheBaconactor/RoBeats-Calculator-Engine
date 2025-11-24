-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:50 PM
-- Time elapsed: 12 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_4 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.LocalShared.ShopLocalProtocol)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.SaleInfo)
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
require(game.ReplicatedStorage.AudioData.NewSongInfo)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SelectableArtists)
local v_u_11 = {
    ["Mode"] = {
        ["Hidden"] = 1
    }
}
v_u_11.new = function(_, p_u_12, p_u_13, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 25 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_11, (copy 3): v_u_5, (copy 4): v_u_1, (copy 5): v_u_4, (copy 6): v_u_7, (copy 7): v_u_8, (copy 8): v_u_3, (copy 9): v_u_9, (copy 10): v_u_10, (copy 11): v_u_6 ]]
    local v17 = {
        ["player_blob_updated"] = function(p16) --[[ Name: player_blob_updated ]] --[[ Line: 68 ]]
            p16:render_song_info()
        end
    }
    local l_Frame_0 = p_u_13.SurfaceGui.Frame
    Vector3.new()
    Vector3.new()
    p_u_13.Parent = p_u_15.Parent
    local v_u_18 = v_u_2:new(p_u_14, p_u_15, p_u_13)
    v17.get_uichild = function(_) --[[ Name: get_uichild ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        return v_u_18;
    end;
    local v_u_19 = -1
    local v_u_20 = -1
    local v_u_21 = nil
    local v_u_22 = nil
    local v_u_23 = nil
    local function _() --[[ Name: cons ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18:layout()
    end;
    v17.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): p_u_13, (ref 2): p_u_14, (ref 3): p_u_15, (ref 4): v_u_18 ]]
        p_u_13:Destroy()
        p_u_13 = nil
        p_u_14 = nil
        p_u_15 = nil
        v_u_18 = nil
    end;
    v17.behaviour_update = function(_, p24, _) --[[ Name: behaviour_update ]] --[[ Line: 58 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_5 ]]
        v_u_18:set_scale(v_u_5:expt_sec(v_u_18:get_scale(), 1, 1, p24))
    end;
    v17.visual_update = function(_, _, _) --[[ Name: visual_update ]] --[[ Line: 62 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18:layout()
    end;
    v17.set_visible = function(_, p25) --[[ Name: set_visible ]] --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): p_u_13 ]]
        p_u_13.SurfaceGui.Enabled = p25
    end;
    v17.render_song_info = function(p26) --[[ Name: render_song_info ]] --[[ Line: 72 ]]
        --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_12, (copy 3): l_Frame_0, (ref 4): v_u_1, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): v_u_22, (ref 8): v_u_8, (ref 9): v_u_3, (ref 10): v_u_9, (ref 11): v_u_10 ]]
        if v_u_19 == -1 then
            return;
        else
            p_u_12._player_blob_manager:get_player_blob()
            local v27 = l_Frame_0
            if v_u_1:obj_has_children_of_names(v27, { "TitleDisplay", "ArtistDisplay", "CoverSection" }) == false then
                return v_u_4:warnf("SongShopUIItem missing children, exit early");
            else
                v27.ArtistIcon.Image = v_u_1:transparent_assetid()
                v27.NewDisplay.Visible = false
                if p26:selected_item_is_sale() then
                    v27.TitleDisplay.Text = v_u_7:get_salecombokey_title(v_u_22)
                    v27.ArtistDisplay.Text = "Limited time sale!"
                    v27.SongDifficultySection.Visible = false
                    v27.CoverSection.AlbumArt.Image = v_u_8:get_shop_image_for_saleid(v_u_22)
                    v27.CoverSection.AlbumArtOverlay.Visible = false
                    v27.CoverSection.ColorSection.Visible = false
                else
                    v27.TitleDisplay.Text = v_u_3:singleton():get_title_for_key(v_u_19)
                    v27.ArtistDisplay.Text = v_u_3:singleton():get_artist_for_key(v_u_19)
                    v27.SongDifficultySection.Visible = true
                    v27.SongDifficultySection.Display.Text = string.format("%d", v_u_3:singleton():get_difficulty_for_key(v_u_19))
                    v27.SongDifficultySection.Display.TextColor3 = v_u_3:singleton():get_difficulty_color_for_key(v_u_19)
                    v_u_3:singleton():render_coverimage_for_key(v27.CoverSection.AlbumArt, v27.CoverSection.AlbumArtOverlay, v_u_19)
                    v_u_9:render_songkey_colorsection(v_u_19, v27.CoverSection.ColorSection)
                    local v28, v29 = v_u_10:artist_name_is_selectable((v_u_3:singleton():get_artist_for_key(v_u_19)))
                    if v28 then
                        local v30 = v_u_10:artist_name_to_icon(v29)
                        if #v30 > 0 then
                            v27.ArtistIcon.Image = v30
                        end;
                    end;
                end;
                if p26:selected_item_is_sale() then
                    v27.DescriptionDisplay.Text = v_u_8:get_shop_description_for_saleid(v_u_22)
                else
                    v27.DescriptionDisplay.Text = v_u_1:string_sub_max_len(v_u_3:singleton():get_description_for_key(v_u_19), 256)
                end;
                if p26:can_purchase() then
                    v27.CoverSection.Visible = true
                    v27.BoughtDisplay.Visible = false
                    v27.PriceSection.Visible = true
                else
                    v27.CoverSection.Visible = true
                    v27.BoughtDisplay.Visible = true
                    v27.PriceSection.Visible = false
                    v27.CoverSection.ColorSection.Visible = false
                end;
            end;
        end;
    end;
    v17.can_purchase = function(_) --[[ Name: can_purchase ]] --[[ Line: 130 ]]
        --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_6, (ref 3): v_u_20 ]]
        return v_u_6:get_count_for_song_shop_saleid(p_u_12._player_blob_manager:get_player_blob(), v_u_20) == 0;
    end;
    v17.set_item_info = function(p31, p32) --[[ Name: set_item_info ]] --[[ Line: 135 ]]
        --[[ Upvalues: (copy 1): l_Frame_0, (ref 2): v_u_19, (ref 3): v_u_20, (ref 4): v_u_21, (ref 5): v_u_22, (ref 6): v_u_23, (ref 7): v_u_6 ]]
        if p32 ~= nil then
            local v33 = l_Frame_0
            v_u_19 = p32.SongKey
            v_u_20 = p32.SaleId
            v_u_21 = p32.SaleDescription
            v_u_22 = p32.SaleComboKey
            v_u_23 = p32.SaleImage
            p31:render_song_info()
            v_u_6:currency_type_render_icon(p32.PriceType, v33.PriceSection.Icon)
            v33.PriceSection.Display.Text = string.format("%d", p32.PriceValue)
        end;
    end;
    v17.animate_item_updated = function(_) --[[ Name: animate_item_updated ]] --[[ Line: 164 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18:set_scale(1.15)
    end;
    v17.get_preview_songkey = function(p34) --[[ Name: get_preview_songkey ]] --[[ Line: 168 ]]
        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_22, (ref 3): v_u_19 ]]
        if p34:selected_item_is_sale() then
            return v_u_8:get_songids_for_saleid(v_u_22):random();
        else
            return v_u_19;
        end;
    end;
    v17.selected_item_is_sale = function(_) --[[ Name: selected_item_is_sale ]] --[[ Line: 177 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22 ~= nil;
    end;
    v17.selected_item_sale_id = function(_) --[[ Name: selected_item_sale_id ]] --[[ Line: 178 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22;
    end;
    v_u_18:layout()
    return v17;
end;
return v_u_11;
